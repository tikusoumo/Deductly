export interface User {
  id: string;
  email: string;
  name: string;
  createdAt: string;
}

export interface ChatSession {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messageCount: number;
  status: 'active' | 'completed' | 'archived';
}

export interface Message {
  id: string;
  content: string;
  sender: 'user' | 'ai';
  timestamp: string;
  type?: 'text' | 'file' | 'suggestion';
}

export interface TaxSubmission {
  id: string;
  title: string;
  status: 'draft' | 'submitted' | 'processing' | 'completed';
  submittedAt?: string;
  documents: string[];
  estimatedSavings?: number;
}

export interface ApiResponse<T> {
  data: T;
  message: string;
  success: boolean;
}

export interface DisabilityDetails {
  is_disabled: boolean;
  type?: 'normal_disability' | 'severe_disability';
}

export interface Investments {
  '80C_investments': number;
  nps_contribution: number;
}

export interface OtherIncome {
  interest_from_savings: number;
  fixed_deposit_interest: number;
}

export interface TaxFormData {
  salary: number;
  user_age: number;
  is_senior_citizen: boolean;
  investments: Investments;
  health_insurance_premium: number;
  parents_health_insurance_premium: number;
  medical_expenses: number;
  parents_age: number;
  housing_loan_interest: number;
  property_status: 'self_occupied' | 'let_out' | 'deemed_let_out';
  donation_amount: number;
  education_loan_interest: number;
  disability_details: DisabilityDetails;
  other_income: OtherIncome;
}

export interface TaxCalculationResult {
  total_tax_liability: number;
  total_deductions: number;
  taxable_income: number;
  estimated_savings: number;
  breakdown: {
    standard_deduction?: number;
    section_80C: number;
    section_80CCD1B?: number;
    section_80D: number;
    section_80G: number;
    section_80E: number;
    section_24: number;
    section_80DD?: number;
    section_80TTA?: number;
    section_80TTB?: number;
  };
}