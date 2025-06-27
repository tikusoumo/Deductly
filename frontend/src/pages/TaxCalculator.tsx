/* eslint-disable @typescript-eslint/no-unused-vars */
import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { useNavigate } from 'react-router-dom';
import { 
  Calculator, 
  DollarSign, 
  Home, 
  Heart, 
  PiggyBank,
  TrendingUp,
  AlertCircle,
  CheckCircle,
  Loader2,
  MessageSquare
} from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Link } from 'react-router-dom';

type TaxFormData = {
  salary: number;
  user_age: number;
  is_senior_citizen: boolean;
  investments: {
    "80C_investments": number;
    nps_contribution: number;
  };
  health_insurance_premium: number;
  parents_health_insurance_premium: number;
  medical_expenses: number;
  parents_age?: number;
  housing_loan_interest: number;
  property_status: 'self_occupied' | 'let_out' | 'deemed_let_out';
  donation_amount: number;
  education_loan_interest: number;
  disability_details: {
    is_disabled: boolean;
    type?: 'normal_disability' | 'severe_disability';
  };
  other_income: {
    interest_from_savings: number;
    fixed_deposit_interest: number;
  };
};

type TaxCalculationResult = {
  total_tax_liability: number;
  total_deductions: number;
  taxable_income: number;
  estimated_savings: number;
  breakdown: Record<string, number>;
  rawResponse?: string;
};

const taxFormSchema = z.object({
  salary: z.number().min(0, 'Salary must be positive'),
  user_age: z.number().min(18, 'Age must be at least 18').max(100, 'Age must be realistic'),
  is_senior_citizen: z.boolean(),
  investments: z.object({
    "80C_investments": z.number().min(0).max(150000, 'Section 80C limit is ₹1,50,000'),
    nps_contribution: z.number().min(0).max(50000, 'NPS additional limit is ₹50,000')
  }),
  health_insurance_premium: z.number().min(0),
  parents_health_insurance_premium: z.number().min(0),
  medical_expenses: z.number().min(0),
  parents_age: z.number().min(0).max(120).optional(),
  housing_loan_interest: z.number().min(0),
  property_status: z.enum(['self_occupied', 'let_out', 'deemed_let_out']),
  donation_amount: z.number().min(0),
  education_loan_interest: z.number().min(0),
  disability_details: z.object({
    is_disabled: z.boolean(),
    type: z.enum(['normal_disability', 'severe_disability']).optional()
  }),
  other_income: z.object({
    interest_from_savings: z.number().min(0),
    fixed_deposit_interest: z.number().min(0)
  })
});

const parseTaxResponse = (response: string): TaxCalculationResult => {
  const deductions: Record<string, number> = {};
  let totalDeductions = 0;
  let taxableIncome = 0;
  let taxLiability = 0;

  // Extract deductions
  const deductionRegex = /- \*\*(.+?)\*\*: ₹([\d,]+)/g;
  let deductionMatch;
  while ((deductionMatch = deductionRegex.exec(response))) {
    const section = deductionMatch[1];
    const amount = parseFloat(deductionMatch[2].replace(/,/g, ''));
    deductions[section] = amount;
    totalDeductions += amount;
  }

  // Extract totals
  const totalsRegex = /\*\*Total Estimated Deductions\*\*: ₹([\d,]+)\n\*\*Total Estimated Taxable Income\*\*: ₹([\d,]+)\n\*\*Total Estimated Tax Liability\*\*: ₹([\d,]+)/;
  const totalsMatch = response.match(totalsRegex);
  if (totalsMatch) {
    totalDeductions = parseFloat(totalsMatch[1].replace(/,/g, ''));
    taxableIncome = parseFloat(totalsMatch[2].replace(/,/g, ''));
    taxLiability = parseFloat(totalsMatch[3].replace(/,/g, ''));
  }

  return {
    total_tax_liability: taxLiability,
    total_deductions: totalDeductions,
    taxable_income: taxableIncome,
    estimated_savings: totalDeductions,
    breakdown: deductions,
    rawResponse: response
  };
};

const formatSectionName = (section: string): string => {
  return section
    .replace(/_/g, ' ')
    .replace(/section/g, 'Section ')
    .replace(/(^|\s)\w/g, match => match.toUpperCase());
};

const getDeductionDescription = (section: string): string => {
  const descriptions: Record<string, string> = {
    standard_deduction: 'Standard deduction for salaried individuals',
    section_24B_deduction: 'Interest on home loan for self-occupied property',
    section_80C_deduction: 'Investments in PPF, ELSS, Life Insurance, etc.',
    section_80CCD1B_deduction: 'Additional NPS contribution (Tier 1 account)',
    section_80D_deduction: 'Health insurance premium for self/family/parents',
    section_80G_deduction: 'Eligible donations to charitable institutions',
    section_80E_deduction: 'Interest on education loan for higher studies',
    section_80DD_deduction: 'Medical treatment of disabled dependent',
    section_80TTA_deduction: 'Interest from savings accounts',
    section_80TTB_deduction: 'Interest income for senior citizens'
  };
  
  return descriptions[section] || 'Tax deduction under this section';
};

export const TaxCalculator: React.FC = () => {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [calculationResult, setCalculationResult] = useState<TaxCalculationResult | null>(null);
  const [isCalculating, setIsCalculating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { register, handleSubmit, watch, setValue, formState: { errors } } = useForm<TaxFormData>({
    resolver: zodResolver(taxFormSchema),
    defaultValues: {
      salary: 0,
      user_age: 25,
      is_senior_citizen: false,
      investments: {
        '80C_investments': 0,
        nps_contribution: 0
      },
      health_insurance_premium: 0,
      parents_health_insurance_premium: 0,
      medical_expenses: 0,
      parents_age: 0,
      housing_loan_interest: 0,
      property_status: 'self_occupied',
      donation_amount: 0,
      education_loan_interest: 0,
      disability_details: {
        is_disabled: false,
        type: undefined
      },
      other_income: {
        interest_from_savings: 0,
        fixed_deposit_interest: 0
      }
    }
  });

  const watchedValues = watch();
  const totalSteps = 5;
  const progress = (currentStep / totalSteps) * 100;

  React.useEffect(() => {
    const age = watchedValues.user_age;
    if (age >= 60) {
      setValue('is_senior_citizen', true);
    } else {
      setValue('is_senior_citizen', false);
    }
  }, [watchedValues.user_age, setValue]);

  const handleCalculateTax = async (data: TaxFormData) => {
    console.log('Form submitted with data:', data);
    setIsCalculating(true);
    setError(null);
    
    try {
      const user = localStorage.getItem('user') ? JSON.parse(localStorage.getItem('user') || '{}') : {};
      const userId = user.id || '';
      
      if (!userId) {
        throw new Error('User ID is required for tax calculation');
      }

      // Prepare the request payload
      const requestPayload = {
        user_details: {
          salary: data.salary,
          user_age: data.user_age,
          is_senior_citizen: data.is_senior_citizen,
          investments: {
            "80C_investments": data.investments["80C_investments"],
            nps_contribution: data.investments.nps_contribution
          },
          health_insurance_premium: data.health_insurance_premium,
          parents_health_insurance_premium: data.parents_health_insurance_premium,
          medical_expenses: data.medical_expenses,
          parents_age: data.parents_age,
          housing_loan_interest: data.housing_loan_interest,
          property_status: data.property_status,
          donation_amount: data.donation_amount,
          education_loan_interest: data.education_loan_interest,
          disability_details: {
            is_disabled: data.disability_details.is_disabled,
            type: data.disability_details.type || null
          },
          other_income: {
            interest_from_savings: data.other_income.interest_from_savings,
            fixed_deposit_interest: data.other_income.fixed_deposit_interest
          }
        }
      };

      console.log('Sending payload:', requestPayload);

      const response = await fetch('http://localhost:8000/chats/start_new_tax_session', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-ID': userId,
        },
        body: JSON.stringify(requestPayload),
      });

      console.log('Response status:', response.status);

      if (!response.ok) {
        const errorData = await response.json();
        console.error('API Error Response:', errorData);
        throw new Error(errorData.message || 'Tax calculation failed');
      }

      const responseData = await response.json();
      console.log('API Response:', responseData);

      // Redirect to chat session page with session_id
      if (responseData.session_id) {
        localStorage.setItem('session_id', responseData.session_id);
        navigate(`/chat?session_id=${responseData.session_id}`, );
        return;
      }

      // Optionally, you can still parse and show results if session_id is not present
      const result = parseTaxResponse(responseData.initial_bot_response || responseData.bot_response);
      setCalculationResult(result);
      setCurrentStep(6);

    } catch (err) {
      console.error('Error in handleCalculateTax:', err);
      const errorMessage = err instanceof Error ? err.message : 'Tax calculation failed';
      setError(errorMessage);
    } finally {
      setIsCalculating(false);
    }
  };

  const nextStep = () => currentStep < totalSteps && setCurrentStep(currentStep + 1);
  const prevStep = () => currentStep > 1 && setCurrentStep(currentStep - 1);

  const renderStep = () => {
    switch (currentStep) {
      case 1:
        return (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <DollarSign className="h-5 w-5 text-green-600" />
                Basic Information
              </CardTitle>
              <CardDescription>
                Let's start with your basic salary and age information
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label htmlFor="salary">Annual Salary (₹)</Label>
                  <Input
                    id="salary"
                    type="number"
                    placeholder="e.g., 850000"
                    {...register('salary', { valueAsNumber: true })}
                  />
                  {errors.salary && (
                    <p className="text-sm text-red-500">{errors.salary.message}</p>
                  )}
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="user_age">Your Age</Label>
                  <Input
                    id="user_age"
                    type="number"
                    placeholder="e.g., 35"
                    {...register('user_age', { valueAsNumber: true })}
                  />
                  {errors.user_age && (
                    <p className="text-sm text-red-500">{errors.user_age.message}</p>
                  )}
                </div>
              </div>

              <div className="flex items-center justify-between p-4 border rounded-lg bg-blue-50">
                <div>
                  <h4 className="font-medium">Senior Citizen Status</h4>
                  <p className="text-sm text-gray-600">
                    {watchedValues.is_senior_citizen 
                      ? 'You qualify for senior citizen benefits (60+ years)'
                      : 'Regular taxpayer status'
                    }
                  </p>
                </div>
                <Badge variant={watchedValues.is_senior_citizen ? 'default' : 'secondary'}>
                  {watchedValues.is_senior_citizen ? 'Senior Citizen' : 'Regular'}
                </Badge>
              </div>
            </CardContent>
          </Card>
        );

      case 2:
        return (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <PiggyBank className="h-5 w-5 text-blue-600" />
                Investments & Savings
              </CardTitle>
              <CardDescription>
                Details about your tax-saving investments
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="80C_investments">Section 80C Investments (₹)</Label>
                  <Input
                    id="80C_investments"
                    type="number"
                    placeholder="e.g., 120000"
                    {...register('investments.80C_investments', { valueAsNumber: true })}
                  />
                  <p className="text-xs text-gray-500">
                    EPF, PPF, Life Insurance, Home Loan Principal, etc. (Max: ₹1,50,000)
                  </p>
                  {errors.investments?.['80C_investments'] && (
                    <p className="text-sm text-red-500">{errors.investments['80C_investments'].message}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="nps_contribution">NPS Contribution (₹)</Label>
                  <Input
                    id="nps_contribution"
                    type="number"
                    placeholder="e.g., 40000"
                    {...register('investments.nps_contribution', { valueAsNumber: true })}
                  />
                  <p className="text-xs text-gray-500">
                    Additional deduction under Section 80CCD(1B) (Max: ₹50,000)
                  </p>
                  {errors.investments?.nps_contribution && (
                    <p className="text-sm text-red-500">{errors.investments.nps_contribution.message}</p>
                  )}
                </div>
              </div>

              <div className="p-4 bg-green-50 rounded-lg">
                <h4 className="font-medium text-green-800 mb-2">Investment Summary</h4>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span>Section 80C:</span>
                    <span>₹{watchedValues.investments?.['80C_investments']?.toLocaleString() || '0'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>NPS (80CCD1B):</span>
                    <span>₹{watchedValues.investments?.nps_contribution?.toLocaleString() || '0'}</span>
                  </div>
                  <Separator className="my-2" />
                  <div className="flex justify-between font-medium">
                    <span>Total Investment Deduction:</span>
                    <span>₹{((watchedValues.investments?.['80C_investments'] || 0) + (watchedValues.investments?.nps_contribution || 0)).toLocaleString()}</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        );

      case 3:
        return (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Heart className="h-5 w-5 text-red-600" />
                Health & Medical
              </CardTitle>
              <CardDescription>
                Health insurance and medical expense details
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label htmlFor="health_insurance_premium">Health Insurance Premium (₹)</Label>
                  <Input
                    id="health_insurance_premium"
                    type="number"
                    placeholder="e.g., 18000"
                    {...register('health_insurance_premium', { valueAsNumber: true })}
                  />
                  <p className="text-xs text-gray-500">For self, spouse, and children</p>
                </div>
  
                <div className="space-y-2">
                  <Label htmlFor="parents_health_insurance_premium">Parents' Health Insurance (₹)</Label>
                  <Input
                    id="parents_health_insurance_premium"
                    type="number"
                    placeholder="e.g., 30000"
                    {...register('parents_health_insurance_premium', { valueAsNumber: true })}
                  />
                </div>
  
                <div className="space-y-2">
                  <Label htmlFor="medical_expenses">Medical Expenses (₹)</Label>
                  <Input
                    id="medical_expenses"
                    type="number"
                    placeholder="e.g., 6000"
                    {...register('medical_expenses', { valueAsNumber: true })}
                  />
                  <p className="text-xs text-gray-500">
                    {watchedValues.is_senior_citizen 
                      ? 'General medical expenses' 
                      : 'Preventive health checkup expenses'
                    }
                  </p>
                </div>
  
                <div className="space-y-2">
                  <Label htmlFor="parents_age">Parents' Age</Label>
                  <Input
                    id="parents_age"
                    type="number"
                    placeholder="e.g., 70"
                    {...register('parents_age', { valueAsNumber: true })}
                  />
                  <p className="text-xs text-gray-500">For determining senior citizen benefits</p>
                </div>
              </div>
  
              <div className="space-y-4">
                <h4 className="font-medium">Disability Details</h4>
                <div className="flex items-center justify-between p-4 border rounded-lg">
                  <div>
                    <Label htmlFor="is_disabled">Dependent with Disability</Label>
                    <p className="text-sm text-gray-600">Section 80DD deduction</p>
                  </div>
                  <Switch
                    id="is_disabled"
                    {...register('disability_details.is_disabled')}
                  />
                </div>
  
                {watchedValues.disability_details?.is_disabled && (
                  <div className="space-y-2">
                    <Label htmlFor="disability_type">Disability Type</Label>
                    <Select 
                      value={watchedValues.disability_details.type}
                      onValueChange={(value) => setValue('disability_details.type', value as 'normal_disability' | 'severe_disability')}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select disability type" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="normal_disability">Normal Disability (40-80%)</SelectItem>
                        <SelectItem value="severe_disability">Severe Disability (80%+)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        );
  
      case 4:
        return (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Home className="h-5 w-5 text-orange-600" />
                Loans & Donations
              </CardTitle>
              <CardDescription>
                Housing loan, education loan, and donation details
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="housing_loan_interest">Housing Loan Interest (₹)</Label>
                  <Input
                    id="housing_loan_interest"
                    type="number"
                    placeholder="e.g., 250000"
                    {...register('housing_loan_interest', { valueAsNumber: true })}
                  />
                </div>
  
                <div className="space-y-2">
                  <Label htmlFor="property_status">Property Status</Label>
                  <Select 
                    value={watchedValues.property_status}
                    onValueChange={(value) => setValue('property_status', value as 'self_occupied' | 'let_out' | 'deemed_let_out')}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="self_occupied">Self Occupied</SelectItem>
                      <SelectItem value="let_out">Let Out</SelectItem>
                      <SelectItem value="deemed_let_out">Deemed Let Out</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
  
                <div className="space-y-2">
                  <Label htmlFor="education_loan_interest">Education Loan Interest (₹)</Label>
                  <Input
                    id="education_loan_interest"
                    type="number"
                    placeholder="e.g., 45000"
                    {...register('education_loan_interest', { valueAsNumber: true })}
                  />
                  <p className="text-xs text-gray-500">Section 80E - No upper limit</p>
                </div>
  
                <div className="space-y-2">
                  <Label htmlFor="donation_amount">Donations (₹)</Label>
                  <Input
                    id="donation_amount"
                    type="number"
                    placeholder="e.g., 5000"
                    {...register('donation_amount', { valueAsNumber: true })}
                  />
                  <p className="text-xs text-gray-500">Section 80G eligible donations</p>
                </div>
              </div>
            </CardContent>
          </Card>
        );
  
      case 5:
        return (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-purple-600" />
                Other Income
              </CardTitle>
              <CardDescription>
                Interest income from savings and fixed deposits
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label htmlFor="interest_from_savings">Savings Account Interest (₹)</Label>
                  <Input
                    id="interest_from_savings"
                    type="number"
                    placeholder="e.g., 8000"
                    {...register('other_income.interest_from_savings', { valueAsNumber: true })}
                  />
                  <p className="text-xs text-gray-500">
                    Section 80TTA - Up to ₹10,000 for regular taxpayers
                  </p>
                </div>
  
                <div className="space-y-2">
                  <Label htmlFor="fixed_deposit_interest">Fixed Deposit Interest (₹)</Label>
                  <Input
                    id="fixed_deposit_interest"
                    type="number"
                    placeholder="e.g., 30000"
                    {...register('other_income.fixed_deposit_interest', { valueAsNumber: true })}
                  />
                  <p className="text-xs text-gray-500">
                    {watchedValues.is_senior_citizen 
                      ? 'Section 80TTB - Up to ₹50,000 for senior citizens'
                      : 'Taxable income for regular taxpayers'
                    }
                  </p>
                </div>
              </div>
  
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  {watchedValues.is_senior_citizen
                    ? 'As a senior citizen, you can claim deduction under Section 80TTB for interest income up to ₹50,000.'
                    : 'You can claim deduction under Section 80TTA for savings account interest up to ₹10,000.'
                  }
                </AlertDescription>
              </Alert>
            </CardContent>
          </Card>
        );

      case 6:
        return calculationResult ? (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-green-600" />
                Tax Calculation Results
              </CardTitle>
              <CardDescription>
                Your personalized tax optimization report
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Summary Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 bg-blue-50 rounded-lg border border-blue-100">
                  <h4 className="font-medium text-blue-800 mb-2">Total Deductions</h4>
                  <p className="text-2xl font-bold text-blue-600">
                    ₹{calculationResult.total_deductions.toLocaleString()}
                  </p>
                </div>
                
                <div className="p-4 bg-green-50 rounded-lg border border-green-100">
                  <h4 className="font-medium text-green-800 mb极简 2">Taxable Income</h4>
                  <p className="text-2xl font-bold text-green-600">
                    ₹{calculationResult.taxable_income.toLocaleString()}
                  </p>
                </div>
                
                <div className="p-4 bg-orange-50 rounded-lg border border-orange-100">
                  <h4 className="font-medium text-orange-800 mb-2">Tax Liability</h4>
                  <p className="text-2xl font-bold text-orange-600">
                    ₹{calculationResult.total_tax_liability.toLocaleString()}
                  </p>
                </div>
              </div>

              {/* Deduction Details */}
              <div className="space-y-4">
                <h3 className="font-semibold text-lg">Deduction Details</h3>
                <div className="space-y-3">
                  {Object.entries(calculationResult.breakdown)
                    .filter(([_, amount]) => amount > 0)
                    .map(([section, amount]) => (
                      <div key={section} className="border rounded-lg p-4">
                        <div className="flex justify-between items-start">
                          <div>
                            <h4 className="font-medium">
                              {formatSectionName(section)}
                            </h4>
                            <p className="text-sm text-gray-600 mt-1">
                              {getDeductionDescription(section)}
                            </p>
                          </div>
                          <Badge variant="outline" className="bg-green-50 text-green-700 px-3 py-1">
                            ₹{amount.toLocaleString()}
                          </Badge>
                        </div>
                      </div>
                    ))}
                </div>
              </div>

              {/* Additional Information */}
              <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                <h4 className="font-medium mb-2">Important Notes</h4>
                <ul className="space-y-2 text-sm text-gray-600 list-disc pl-5">
                  <li>This calculation is based on the old tax regime</li>
                  <li>Standard deduction of ₹50,000 is included</li>
                  <li>Consult a tax professional for personalized advice</li>
                  <li>Tax laws are subject to change</li>
                </ul>
              </div>

              {/* Chat CTA */}
              <div className="mt-6 text-center">
                <p className="mb-2 text-gray-700">Have questions about your deductions?</p>
                <Link to="/chat">
                  <Button>
                    <MessageSquare className="mr-2 h-4 w-4" />
                    Chat with Tax Advisor
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>Calculation Results</CardTitle>
            </CardHeader>
            <CardContent className="text-center py-8">
              <Loader2 className="mx-auto h-8 w-8 animate-spin text-gray-400 mb-4" />
              <p>Processing your tax calculation...</p>
            </CardContent>
          </Card>
        );

      default:
        return null;
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

          <div className="max-w-4xl mx-auto space-y-6">
            {/* Progress Bar */}
            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold">Tax Information Form</h2>
                  <Badge variant="outline">
                    Step {currentStep} of {calculationResult ? 6 : totalSteps}
                  </Badge>
                </div>
                <Progress value={progress} className="h-2" />
                <p className="text-sm text-gray-600 mt-2">
                  {currentStep === 6 ? 'Calculation Complete' : `${Math.round(progress)}% Complete`}
                </p>
              </CardContent>
            </Card>

            {/* Form Steps */}
            <form onSubmit={handleSubmit(handleCalculateTax)}>
              {renderStep()}

              {/* Navigation Buttons */}
              <div className="flex justify-between">
                <Button
                  type="button"
                  variant="outline"
                  onClick={prevStep}
                  disabled={currentStep === 1 || currentStep === 6}
                >
                  Previous
                </Button>

                <div className="flex gap-2">
                  {currentStep < totalSteps && (
                    <Button type="button" onClick={nextStep}>
                      Next
                    </Button>
                  )}
                  
                  {currentStep === totalSteps && (
                    <Button 
                      type="submit" 
                      disabled={isCalculating}
                    >
                      {isCalculating ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Calculating...
                        </>
                      ) : (
                        <>
                          <Calculator className="mr-2 h-4 w-4" />
                          Calculate Tax
                        </>
                      )}
                    </Button>
                  )}
                </div>
              </div>
            </form>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};