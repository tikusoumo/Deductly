import json
from typing import Any, Dict, List

class TaxCalculator:
    """
    A class to calculate various tax deductions based on Indian Income Tax laws
    for Financial Year 2024-25 (Assessment Year 2025-26).
    """

    # --- Constants for Financial Year 2024-25 (AY 2025-26) ---
    STANDARD_DEDUCTION_LIMIT_OLD_REGIME = 50000
    # The new tax regime does not have a standard deduction for salaried individuals
    # but for AY 2024-25, a standard deduction of Rs. 50,000 is allowed.
    # For AY 2025-26, it's typically still Rs. 50,000 for salaried in new regime as well,
    # if gross total income exceeds Rs. 15.3 Lakhs. Let's keep it simple for now based on prompt.

    SECTION_80C_LIMIT = 150000
    SECTION_80CCD1B_LIMIT = 50000 # Additional NPS deduction

    SECTION_80D_SELF_FAMILY_BELOW_60 = 25000
    SECTION_80D_PARENTS_BELOW_60 = 25000
    SECTION_80D_SENIOR_CITIZEN = 50000 # For individuals 60 years or above
    SECTION_80D_PREVENTIVE_HEALTH_CHECKUP_LIMIT = 5000 # Within overall 80D limits

    SECTION_24B_SELF_OCCUPIED_LIMIT = 200000 # For self-occupied property
    SECTION_24B_LET_OUT_OR_DEEMED_LET_OUT_LIMIT = float('inf') # No limit for let-out property

    SECTION_80TTB_LIMIT = 50000 # For senior citizens on interest from deposits
    SECTION_80TTA_LIMIT = 10000 # For non-senior citizens on savings interest

    def __init__(self, user_details: Dict[str, Any]):
        self.user_details = user_details
        
        # Normalize age field: prefer 'user_age' if 'age_self' is missing
        if 'user_age' in self.user_details and 'age_self' not in self.user_details:
            self.user_details['age_self'] = self.user_details['user_age']
        
        # Normalize senior citizen status (string to boolean if applicable)
        if isinstance(self.user_details.get('is_senior_citizen'), str):
            self.user_details['is_senior_citizen'] = self.user_details['is_senior_citizen'].lower() == 'true'

    def calculate_standard_deduction(self, tax_regime: str = "old") -> Dict[str, Any]:
        """
        Calculates Standard Deduction under Section 16(ia).
        """
        salary = self.user_details.get("salary", 0)
        deduction_amount = 0
        summary = ""
        citations = ["Section 16(ia)"]

        # For FY 2024-25 (AY 2025-26), standard deduction is generally Rs. 50,000
        # for salaried individuals, regardless of old or new tax regime for most cases.
        # However, if explicitly differentiating, new regime for higher income might not get it.
        # Sticking to the common understanding for salaried:
        deduction_amount = min(salary, self.STANDARD_DEDUCTION_LIMIT_OLD_REGIME)
        summary = (
            f"The standard deduction in the old tax regime is ₹{self.STANDARD_DEDUCTION_LIMIT_OLD_REGIME:,} "
            f"or salary, whichever is lower. Since the salary is ₹{salary:,}, "
            f"the standard deduction is capped at ₹{deduction_amount:,}."
        )

        return {
            "amount": f"₹{deduction_amount:,}",
            "summary": summary,
            "citations": citations,
        }

    def calculate_section_80C_deduction(self) -> Dict[str, Any]:
        """
        Calculates deduction under Section 80C.
        """
        investments_80c = self.user_details.get("investments", {}).get("80C_investments", 0)
        
        deduction_amount = min(investments_80c, self.SECTION_80C_LIMIT)
        summary = (
            f"Investments under Section 80C (like EPF, PPF, Life Insurance premium, Home Loan Principal repayment, etc.) "
            f"are deductible up to a maximum of ₹{self.SECTION_80C_LIMIT:,}. "
            f"User's 80C investments are ₹{investments_80c:,}. "
            f"Therefore, the deductible amount is ₹{deduction_amount:,}."
        )
        return {
            "amount": f"₹{deduction_amount:,}",
            "summary": summary,
            "citations": ["Section 80C"],
        }

    def calculate_section_80D_deduction(self) -> Dict[str, Any]:
        """
        Calculates deduction under Section 80D for health insurance premiums and medical expenses.
        """
        health_insurance_premium_self = self.user_details.get("health_insurance_premium", 0)
        parents_health_insurance_premium = self.user_details.get("parents_health_insurance_premium", 0)
        medical_expenses = self.user_details.get("medical_expenses", 0) # Could be general medical expenses or preventive checkups
        age_self = self.user_details.get("age_self", 0)
        age_parents = self.user_details.get("parents_age", 0)

        total_80D_deduction = 0
        summary_parts = []
        citations = ["Section 80D"]

        # Part 1: Self, Spouse, Dependent Children
        # If user is senior citizen, the limit is higher (50k for premium + medical).
        # Otherwise, 25k (premium + medical checkup).
        limit_self_family = self.SECTION_80D_SELF_FAMILY_BELOW_60
        if age_self >= 60:
            limit_self_family = self.SECTION_80D_SENIOR_CITIZEN
            
        deductible_self_family_premium = min(health_insurance_premium_self, limit_self_family)
        remaining_self_family_limit = limit_self_family - deductible_self_family_premium
        
        # Consider general medical expenses for senior citizens if applicable within their 50k limit
        deductible_self_family_medical = 0
        if age_self >= 60: # For senior citizens, medical expenses are covered under 50k
            deductible_self_family_medical = min(medical_expenses, remaining_self_family_limit)
            # Adjust medical_expenses as some might be consumed here
            medical_expenses_remaining = medical_expenses - deductible_self_family_medical
        else:
            # For non-senior citizens, medical expenses are usually limited to preventive checkups within the 5k sub-limit
            # We'll treat medical_expenses here as preventive for non-seniors if not explicitly separated
            deductible_self_family_medical = min(medical_expenses, self.SECTION_80D_PREVENTIVE_HEALTH_CHECKUP_LIMIT, remaining_self_family_limit)
            medical_expenses_remaining = medical_expenses - deductible_self_family_medical # Update remaining medical expenses

        section_80D_self_family = deductible_self_family_premium + deductible_self_family_medical
        section_80D_self_family = min(section_80D_self_family, limit_self_family) # Final cap
        
        if section_80D_self_family > 0:
            summary_parts.append(
                f"Health insurance premium/medical expenses for self/family: ₹{section_80D_self_family:,} (max ₹{limit_self_family:,})."
            )
        total_80D_deduction += section_80D_self_family


        # Part 2: Parents
        limit_parents = self.SECTION_80D_PARENTS_BELOW_60
        if age_parents >= 60:
            limit_parents = self.SECTION_80D_SENIOR_CITIZEN

        deductible_parents_premium = min(parents_health_insurance_premium, limit_parents)
        remaining_parents_limit = limit_parents - deductible_parents_premium
        
        # Any remaining medical expenses from user_details could be for parents if applicable (assuming not part of premium)
        deductible_parents_medical = 0
        if age_parents >= 60: # For senior citizen parents, general medical expenses covered under 50k
             deductible_parents_medical = min(medical_expenses_remaining if 'medical_expenses_remaining' in locals() else medical_expenses, remaining_parents_limit)
        else: # For non-senior parents, only preventive checkup if separate, or within 25k limit
            deductible_parents_medical = min(medical_expenses_remaining if 'medical_expenses_remaining' in locals() else medical_expenses, self.SECTION_80D_PREVENTIVE_HEALTH_CHECKUP_LIMIT, remaining_parents_limit)

        section_80D_parents = deductible_parents_premium + deductible_parents_medical
        section_80D_parents = min(section_80D_parents, limit_parents) # Final cap

        if section_80D_parents > 0:
            summary_parts.append(
                f"Health insurance premium/medical expenses for parents: ₹{section_80D_parents:,} (max ₹{limit_parents:,})."
            )
        total_80D_deduction += section_80D_parents
        
        # General preventive health checkup - often assumed to be part of the medical expenses already
        # if medical_expenses > 0 and self.SECTION_80D_PREVENTIVE_HEALTH_CHECKUP_LIMIT > 0:
        #     # Ensure it's not double counted if already covered above
        #     # This logic depends on how user categorizes 'medical_expenses' vs 'preventive_health_checkup'
        #     # For simplicity, if medical_expenses is provided, we can assume it covers preventive.
        #     pass

        summary = ". ".join(summary_parts) if summary_parts else "No deduction under Section 80D."
        
        return {
            "amount": f"₹{total_80D_deduction:,}",
            "summary": summary,
            "citations": citations,
        }

    def calculate_section_24B_deduction(self) -> Dict[str, Any]:
        """
        Calculates deduction for interest on housing loan under Section 24(b).
        """
        housing_loan_interest = self.user_details.get("housing_loan_interest", 0)
        property_status = self.user_details.get("property_status", "").lower()

        deduction_amount = 0
        summary = ""
        citations = ["Section 24(b)"]

        if property_status == "self_occupied":
            deduction_amount = min(housing_loan_interest, self.SECTION_24B_SELF_OCCUPIED_LIMIT)
            summary = (
                f"For a self-occupied property, interest on housing loan (₹{housing_loan_interest:,}) "
                f"is deductible up to a maximum of ₹{self.SECTION_24B_SELF_OCCUPIED_LIMIT:,}. "
                f"Therefore, the deductible amount is ₹{deduction_amount:,}."
            )
        elif property_status in ["let_out", "deemed_let_out"]:
            deduction_amount = housing_loan_interest # No limit for let-out property
            summary = (
                f"For a {property_status.replace('_', ' ')} property, the entire interest on housing loan (₹{housing_loan_interest:,}) "
                f"is deductible under Section 24(b)."
            )
        else:
            summary = "Property status not specified or recognized, no deduction under Section 24(b)."

        return {
            "amount": f"₹{deduction_amount:,}",
            "summary": summary,
            "citations": citations,
        }

    def calculate_section_80G_deduction(self) -> Dict[str, Any]:
        """
        Calculates deduction for donations under Section 80G.
        Note: This is a simplified calculation. Actual 80G is complex (100%/50%, with/without AGTI limit).
        """
        donation_amount = self.user_details.get("donation_amount", 0)

        deduction_amount = 0
        summary = "No deduction under Section 80G."
        citations = ["Section 80G"]

        if donation_amount > 0:
            # Assuming donation is to a qualifying institution and is eligible for 100% or 50% without AGTI limit for simplicity,
            # or that the AGTI limit calculation happens later.
            # Cash donations over 2000 are not eligible.
            # Here, we assume non-cash or cash <= 2000 if amount > 2000.
            deduction_amount = donation_amount
            summary = (
                f"The user donated ₹{donation_amount:,}. Assuming this donation was made via a non-cash method "
                f"as it exceeds ₹2,000, or cash <= ₹2,000. Assuming the donation was made to a qualifying institution. "
                f"The full amount of ₹{deduction_amount:,} is potentially deductible. "
                f"However, note that certain donations under Section 80G are subject to a limit of 10% "
                f"of Adjusted Gross Total Income (AGTI), which requires calculating all other deductions first."
            )
            citations.extend(["Section 80G(4)", "Section 80G(5)"])
        
        return {
            "amount": f"₹{deduction_amount:,}",
            "summary": summary,
            "citations": citations,
        }

    def calculate_section_80CCD1B_deduction(self) -> Dict[str, Any]:
        """
        Calculates additional deduction for NPS contribution under Section 80CCD(1B).
        """
        nps_contribution = self.user_details.get("investments", {}).get("nps_contribution", 0)

        deduction_amount = min(nps_contribution, self.SECTION_80CCD1B_LIMIT)
        summary = (
            f"An additional deduction for National Pension System (NPS) contributions under Section 80CCD(1B) "
            f"is allowed up to ₹{self.SECTION_80CCD1B_LIMIT:,}. User's NPS contribution is ₹{nps_contribution:,}. "
            f"Therefore, the deductible amount is ₹{deduction_amount:,}."
        )
        return {
            "amount": f"₹{deduction_amount:,}",
            "summary": summary,
            "citations": ["Section 80CCD(1B)"],
        }

    def calculate_section_80E_deduction(self) -> Dict[str, Any]:
        """
        Calculates deduction for interest on education loan under Section 80E.
        """
        education_loan_interest = self.user_details.get("education_loan_interest", 0)

        deduction_amount = education_loan_interest # No maximum limit on amount
        summary = (
            f"Interest paid on education loan (₹{education_loan_interest:,}) is fully deductible under Section 80E "
            f"for up to 8 consecutive assessment years or until interest is paid, whichever is earlier. "
            f"Therefore, the deductible amount is ₹{deduction_amount:,}."
        )
        return {
            "amount": f"₹{deduction_amount:,}",
            "summary": summary,
            "citations": ["Section 80E"],
        }

    def calculate_section_80DD_deduction(self) -> Dict[str, Any]:
        """
        Calculates deduction for maintenance including medical treatment of a disabled dependent under Section 80DD.
        """
        is_disabled = self.user_details.get("disability_details", {}).get("is_disabled")
        disability_type = self.user_details.get("disability_details", {}).get("type")

        deduction_amount = 0
        summary = "No deduction under Section 80DD as no dependent with disability is indicated in user details."
        citations = ["Section 80DD"]

        if is_disabled == "true": # Assuming 'true' as string from input
            if disability_type == "normal_disability":
                deduction_amount = 75000
                summary = "Deduction for normal disability (40% or more but less than 80%) under Section 80DD is ₹75,000."
                citations.append("Section 80DD(1)")
            elif disability_type == "severe_disability":
                deduction_amount = 125000
                summary = "Deduction for severe disability (80% or more) under Section 80DD is ₹125,000."
                citations.append("Section 80DD(2)")
            else:
                summary = "Disability type not specified or recognized for Section 80DD."
        
        return {
            "amount": f"₹{deduction_amount:,}",
            "summary": summary,
            "citations": citations,
        }

    def calculate_section_80TTA_deduction(self) -> Dict[str, Any]:
        """
        Calculates deduction for interest on savings bank accounts under Section 80TTA.
        Applicable to individuals (other than senior citizens) and HUF.
        """
        age_self = self.user_details.get("age_self", 0)
        interest_from_savings = self.user_details.get("other_income", {}).get("interest_from_savings", 0)

        deduction_amount = 0
        summary = ""
        citations = ["Section 80TTA"]

        if age_self < 60: # Not a senior citizen
            deduction_amount = min(interest_from_savings, self.SECTION_80TTA_LIMIT)
            summary = (
                f"Interest income from savings account (₹{interest_from_savings:,}) is deductible under Section 80TTA "
                f"up to a maximum of ₹{self.SECTION_80TTA_LIMIT:,} for individuals below 60 years of age. "
                f"Therefore, the deductible amount is ₹{deduction_amount:,}."
            )
        else:
            summary = "Section 80TTA is not applicable as the user is a senior citizen. Refer to Section 80TTB."
        
        return {
            "amount": f"₹{deduction_amount:,}",
            "summary": summary,
            "citations": citations,
        }

    def calculate_section_80TTB_deduction(self) -> Dict[str, Any]:
        """
        Calculates deduction for interest income from deposits for senior citizens under Section 80TTB.
        Covers interest from savings accounts, fixed deposits, recurring deposits.
        Maximum deduction is ₹50,000.
        """
        age_self = self.user_details.get("age_self", 0)
        interest_from_savings = self.user_details.get("other_income", {}).get("interest_from_savings", 0)
        fixed_deposit_interest = self.user_details.get("other_income", {}).get("fixed_deposit_interest", 0)
        
        total_interest_income = interest_from_savings + fixed_deposit_interest
        
        deduction_amount = 0
        summary = ""
        citations = ["Section 80TTB"]

        if age_self >= 60: # Senior citizen
            deduction_amount = min(total_interest_income, self.SECTION_80TTB_LIMIT)
            summary = (
                f"As a resident senior citizen (60 years or above), interest income from deposits (₹{total_interest_income:,}) "
                f"is deductible under Section 80TTB up to a maximum of ₹{self.SECTION_80TTB_LIMIT:,}. "
                f"Therefore, the deductible amount is ₹{deduction_amount:,}."
            )
        else:
            summary = "Section 80TTB is not applicable as the user is not a senior citizen. Refer to Section 80TTA."
        
        return {
            "amount": f"₹{deduction_amount:,}",
            "summary": summary,
            "citations": citations,
        }
    def calculate_gross_income(self) -> float:
        """
        Calculates the total gross income from various sources.
        You might need to expand this based on all possible income types in your user_details.
        """
        salary = self.user_details.get("salary", 0)
        other_income = self.user_details.get("other_income", {})
        interest_from_savings = other_income.get("interest_from_savings", 0)
        fixed_deposit_interest = other_income.get("fixed_deposit_interest", 0)
        # Add any other income categories as needed, e.g., house_property_income, capital_gains, business_income
        
        gross_income = salary + interest_from_savings + fixed_deposit_interest
        return gross_income

    def calculate_tax_liability(self, taxable_income: float) -> float:
        """
        Calculates the tax liability based on the taxable income for FY 2024-25 (AY 2025-26).
        This implementation covers both Old and New Tax Regimes, considering age for the Old Regime.
        """
        tax_regime = self.user_details.get("tax_regime", "old").lower() # Default to old if not specified
        user_age = self.user_details.get("age_self", 0) # Assumes 'age_self' is available and an integer
        
        tax_due = 0.0

        if tax_regime == "new":
            # New Tax Regime Slabs for AY 2025-26 (effective from FY 2023-24)
            # Standard deduction of Rs. 50,000 is implicitly handled before passing taxable_income here
            # or should be handled by an initial reduction in gross income.
            # Assuming taxable_income already has standard deduction applied if applicable
            # The new regime also allows a standard deduction for salaried individuals if opted.
            # However, for simplicity here, we assume standard deduction is already accounted for in taxable_income
            # if the user opted for the new regime and is eligible.
            
            if taxable_income <= 300000:
                tax_due = 0
            elif taxable_income <= 600000:
                tax_due = (taxable_income - 300000) * 0.05
            elif taxable_income <= 900000:
                tax_due = 15000 + (taxable_income - 600000) * 0.10
            elif taxable_income <= 1200000:
                tax_due = 45000 + (taxable_income - 900000) * 0.15
            elif taxable_income <= 1500000:
                tax_due = 90000 + (taxable_income - 1200000) * 0.20
            else: # Above 15,00,000
                tax_due = 150000 + (taxable_income - 1500000) * 0.30
            
            # Rebate under Section 87A for income up to ₹7 Lakhs (for new regime)
            if taxable_income <= 700000:
                tax_due = max(0, tax_due - 25000) # Rebate up to ₹25,000
            
        else: # Old Tax Regime Slabs for AY 2025-26
            if user_age < 60: # Individuals below 60 years (Resident/Non-Resident)
                if taxable_income <= 250000:
                    tax_due = 0
                elif taxable_income <= 500000:
                    tax_due = (taxable_income - 250000) * 0.05
                elif taxable_income <= 1000000:
                    tax_due = 12500 + (taxable_income - 500000) * 0.20
                else: # Above 10,00,000
                    tax_due = 112500 + (taxable_income - 1000000) * 0.30
                
                # Rebate under Section 87A for income up to ₹5 Lakhs (for old regime)
                if taxable_income <= 500000:
                    tax_due = max(0, tax_due - 12500) # Rebate up to ₹12,500

            elif 60 <= user_age < 80: # Senior Citizens (60 to less than 80 years)
                if taxable_income <= 300000:
                    tax_due = 0
                elif taxable_income <= 500000:
                    tax_due = (taxable_income - 300000) * 0.05
                elif taxable_income <= 1000000:
                    tax_due = 10000 + (taxable_income - 500000) * 0.20
                else: # Above 10,00,000
                    tax_due = 110000 + (taxable_income - 1000000) * 0.30
                
                # Rebate under Section 87A for income up to ₹5 Lakhs (for old regime)
                if taxable_income <= 500000:
                    tax_due = max(0, tax_due - 12500)

            else: # Super Senior Citizens (80 years and above)
                if taxable_income <= 500000:
                    tax_due = 0
                elif taxable_income <= 1000000:
                    tax_due = (taxable_income - 500000) * 0.20
                else: # Above 10,00,000
                    tax_due = 100000 + (taxable_income - 1000000) * 0.30

                # Section 87A rebate not applicable for Super Senior Citizens as their basic exemption is already ₹5 Lakhs.

        # Add Health and Education Cess @ 4%
        tax_due += tax_due * 0.04
        
        # Surcharge (if applicable) - Simplified: Not implemented here.
        # Surcharge rates vary based on income levels (e.g., 10%, 15%, 25%, 37%).
        # This would require an additional check for income exceeding specific thresholds (e.g., ₹50 Lakhs, ₹1 Crore).

        return tax_due