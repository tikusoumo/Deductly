from fastapi.responses import JSONResponse
from models.tax_model import TaxFormRequest
from rag_pipeline.main_graph import graph
# from rag_pipeline.tax_deductions import TaxDeductions
import asyncio
async def submit_tax_data(data: TaxFormRequest):
    dict_data = data
    final_result = await graph.ainvoke(dict_data)
    verdict_text = final_result.get("verdict", "No detailed tax verdict could be generated.")
    print(f"output: {verdict_text}")  # ✅ Correct
    return JSONResponse(
        content={
            "message": "Tax data submitted successfully",
            "data": verdict_text
        },
        status_code=200
    )
