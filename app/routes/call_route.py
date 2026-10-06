import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.Auth.dependencies import get_current_tenant
from app.core.config import get_settings
from app.core.database import get_db
from app.models.call import Call
from app.models.tenant import Tenant
from app.repositories.call_repo import CallRepository
from app.repositories.customer_repo import CustomerRepository
from app.schemas.call_schema import (
    CallResponse,
    OutboundCallRequest,
    OutboundCallResponse,
)
from app.voice.twillio import create_outbound_call
from app.repositories.agent_repo import AgentRepository
from app.repositories.campaign_repo import CampaignRepository


router = APIRouter(
    prefix="/calls",
    tags=["calls"],
)

call_repository = CallRepository()
customer_repository = CustomerRepository()
agent_repository = AgentRepository()
campaign_repository = CampaignRepository()
settings = get_settings()


@router.get(
    "",
    response_model=list[CallResponse],
)
async def list_calls(
        tenant: Tenant = Depends(get_current_tenant),
        db: AsyncSession = Depends(get_db),
):
    calls = await call_repository.list_for_tenant(
        session=db,
        tenant_id=tenant.id,
    )

    return calls


@router.post(
    "/outbound",
    response_model=OutboundCallResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_outbound_call_for_tenant(
        payload: OutboundCallRequest,
        tenant: Tenant = Depends(get_current_tenant),
        db: AsyncSession = Depends(get_db),
):
    # The client supplies only the customer identity. The tenant is
    # always derived from the authenticated user on the server.
    customer = await customer_repository.get_by_id_for_tenant(
        session=db,
        customer_id=payload.customer_id,
        tenant_id=tenant.id,
    )

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )


    agent = await agent_repository.get_by_id_for_tenant(
            session=db,
            agent_id=payload.agent_id,
            tenant_id=tenant.id,
        )

    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )


    campaign = None

    if payload.campaign_id is not None:
        campaign = await campaign_repository.get_by_id_for_tenant(
            session=db,
            campaign_id=payload.campaign_id,
            tenant_id=tenant.id,
        )

        if campaign is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found",
            )

        if campaign.agent_id != agent.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Campaign does not belong to selected agent",
            )



    # Establish durable ownership before contacting Twilio.
    call_record = Call(
        tenant_id=tenant.id,
        customer_id=customer.id,
        agent_id=agent.id,
        campaign_id=campaign.id if campaign else None,
        status="initiating",
    )


    db.add(call_record)
    await db.commit()
    await db.refresh(call_record)

    twiml_url = (
        f"{settings.public_base_url}/voice/twiml"
    )

    try:
        twilio_call = await asyncio.to_thread(
            create_outbound_call,
            customer.phone_number,
            twiml_url,
        )
    except Exception as exc:
        call_record.status = "failed"
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to initiate outbound call",
        ) from exc

    call_record.twilio_call_sid = twilio_call.sid
    call_record.status = "initiated"

    await db.commit()
    await db.refresh(call_record)

    return call_record


@router.get(
    "/{call_id}",
    response_model=CallResponse,
)
async def get_call(
        call_id: int,
        tenant: Tenant = Depends(get_current_tenant),
        db: AsyncSession = Depends(get_db),
):
    call = await call_repository.get_by_id_for_tenant(
        session=db,
        call_id=call_id,
        tenant_id=tenant.id,
    )

    if call is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found",
        )

    return call
