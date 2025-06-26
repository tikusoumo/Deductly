# from pydantic import BaseModel
# from typing import Optional, Dict

# class DeductionField(BaseModel):
#     enabled: bool
#     amount: Optional[str]

# class TaxFormRequest(BaseModel):
#     personalInfo: Dict[str, str]
#     incomeDetails: Dict[str, str]
#     section80C: Dict[str, DeductionField]
#     otherDeductions: Dict[str, DeductionField]
#     housingDetails: Dict[str, str]
#     miscellaneous: Dict[str, str]
from pydantic import BaseModel
from typing import Any, Literal, Dict



class TaxFormRequest(BaseModel):
    user_details: Dict[str, Any]
