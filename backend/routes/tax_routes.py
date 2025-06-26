from fastapi import APIRouter
from models.tax_model import TaxFormRequest
from controllers.tax_controller import submit_tax_data

router = APIRouter()

@router.post("/submit")
async def handle_tax_submission(data: TaxFormRequest):
    return await submit_tax_data(data)
