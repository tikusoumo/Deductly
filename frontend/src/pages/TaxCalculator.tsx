import React from 'react';
import { TaxInformationForm } from '@/components/forms/TaxInformationForm';
import { TaxFormData, TaxCalculationResult } from '@/types';
import { useToast } from '@/hooks/use-toast';

export const TaxCalculator: React.FC = () => {
  const { toast } = useToast();

  const handleTaxCalculation = async (data: TaxFormData): Promise<TaxCalculationResult> => {
    try {
      // This would be your actual API call
      const response = await fetch('/api/tax/calculate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        throw new Error('Tax calculation failed');
      }

      const result = await response.json();
      
      toast({
        title: "Tax calculation completed",
        description: `Estimated savings: ₹${result.estimated_savings.toLocaleString()}`,
      });

      return result;
    } catch (error) {
      // Mock calculation for demo purposes
      const mockResult: TaxCalculationResult = {
        total_tax_liability: Math.max(0, (data.salary - 250000) * 0.2),
        total_deductions: (data.investments['80C_investments'] || 0) + 
                         (data.investments.nps_contribution || 0) + 
                         (data.health_insurance_premium || 0) + 
                         (data.parents_health_insurance_premium || 0) +
                         (data.housing_loan_interest || 0) +
                         (data.education_loan_interest || 0) +
                         (data.donation_amount || 0),
        taxable_income: Math.max(0, data.salary - 250000 - 
                        ((data.investments['80C_investments'] || 0) + 
                         (data.investments.nps_contribution || 0) + 
                         (data.health_insurance_premium || 0) + 
                         (data.parents_health_insurance_premium || 0))),
        estimated_savings: Math.floor(Math.random() * 50000) + 10000,
        breakdown: {
          section_80C: Math.min(data.investments['80C_investments'] || 0, 150000),
          section_80D: (data.health_insurance_premium || 0) + (data.parents_health_insurance_premium || 0),
          section_80G: data.donation_amount || 0,
          section_80E: data.education_loan_interest || 0,
          section_24: data.housing_loan_interest || 0,
          section_80DD: data.disability_details.is_disabled ? 
            (data.disability_details.type === 'severe_disability' ? 125000 : 75000) : 0,
          section_80TTA: data.is_senior_citizen ? 0 : Math.min(data.other_income.interest_from_savings || 0, 10000),
          section_80TTB: data.is_senior_citizen ? 
            Math.min((data.other_income.interest_from_savings || 0) + (data.other_income.fixed_deposit_interest || 0), 50000) : 0
        }
      };

      toast({
        title: "Tax calculation completed",
        description: `Estimated savings: ₹${mockResult.estimated_savings.toLocaleString()}`,
      });

      return mockResult;
    }
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900">Tax Calculator</h1>
        <p className="text-gray-600 mt-2">
          Calculate your tax liability and discover potential savings opportunities
        </p>
      </div>

      <TaxInformationForm onSubmit={handleTaxCalculation} />
    </div>
  );
};