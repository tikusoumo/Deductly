import React from 'react';
import { TaxInformationForm } from '@/components/forms/TaxInformationForm';
import { TaxFormData, TaxCalculationResult } from '@/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { AlertCircle } from 'lucide-react';

export const TaxCalculator: React.FC = () => {
  const [error, setError] = React.useState<string | null>(null);

  const handleCalculateTax = async (data: TaxFormData): Promise<TaxCalculationResult> => {
    setError(null);
    try {
      // This assumes the API endpoint is '/api/tax/submit' and returns a structured JSON
      // object containing the full results from the RAG pipeline.
      const { id } = localStorage.getItem('user') ? JSON.parse(localStorage.getItem('user') || '{}') : { id: null };
      const response = await fetch('http://localhost:8000/chats/start_new_tax_session', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'user-id': id || '',
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'An error occurred during tax calculation.');
      }

      const responseData = await response.json();
      const backendResult = responseData.data;

      // Transforms the backend response into the TaxCalculationResult type expected by the form.
      const parseAmount = (amountStr: string | number | undefined): number => {
        if (typeof amountStr === 'number') return amountStr;
        if (typeof amountStr !== 'string' || amountStr === 'N/A') return 0;
        const numbers = amountStr.replace(/[^0-9.]/g, '');
        return numbers ? parseFloat(numbers) : 0;
      };

      const reasoning = backendResult.reasoning || {};
      const breakdown: TaxCalculationResult['breakdown'] = {
        standard_deduction: parseAmount(reasoning.standard_deduction?.amount),
        section_80C: parseAmount(reasoning.section_80C_deduction?.amount),
        section_80CCD1B: parseAmount(reasoning.section_80CCD1B_deduction?.amount),
        section_80D: parseAmount(reasoning.section_80D_deduction?.amount),
        section_80G: parseAmount(reasoning.section_80G_deduction?.amount),
        section_80E: parseAmount(reasoning.section_80E_deduction?.amount),
        section_24: parseAmount(reasoning.section_24B_deduction?.amount),
        section_80DD: parseAmount(reasoning.section_80DD_deduction?.amount),
        section_80TTA: parseAmount(reasoning.section_80TTA_deduction?.amount),
        section_80TTB: parseAmount(reasoning.section_80TTB_deduction?.amount),
      };

      // Assumes the backend calculates and provides estimated_savings.
      const estimatedSavings = backendResult.estimated_savings || 0;

      const resultForFrontend: TaxCalculationResult = {
        total_tax_liability: backendResult.tax_liability || 0,
        total_deductions: backendResult.total_deductions || 0,
        taxable_income: backendResult.total_taxable_income || 0,
        estimated_savings: estimatedSavings,
        breakdown: breakdown,
      };

      return resultForFrontend;

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred.';
      setError(errorMessage);
      throw new Error(errorMessage); // Re-throw for the form's internal error handling
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">Tax Calculator</CardTitle>
          <CardDescription>
            Fill in your financial details to calculate your tax liability and discover potential savings.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Calculation Failed</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          <TaxInformationForm onSubmit={handleCalculateTax} />
        </CardContent>
      </Card>
    </div>
  );
}