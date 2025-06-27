/* eslint-disable @typescript-eslint/no-unused-vars */
import React, { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { useNavigate } from "react-router-dom";
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
  MessageSquare,
  User,
  Users,
} from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Link } from "react-router-dom";

// This is the schema for the data sent to the backend. It remains UNCHANGED.
const taxFormSchema = z.object({
  salary: z.number().min(0, "Salary must be positive"),
  user_age: z
    .number()
    .min(18, "Age must be at least 18")
    .max(100, "Age must be realistic"),
  is_senior_citizen: z.boolean(),
  investments: z.object({
    "80C_investments": z
      .number()
      .min(0)
      .max(150000, "Section 80C limit is ₹1,50,000"),
    nps_contribution: z
      .number()
      .min(0)
      .max(50000, "NPS additional limit is ₹50,000"),
  }),
  health_insurance_premium: z.number().min(0),
  parents_health_insurance_premium: z.number().min(0),
  medical_expenses: z.number().min(0),
  parents_age: z.number().min(0).max(120).optional(),
  housing_loan_interest: z.number().min(0),
  property_status: z.enum(["self_occupied", "let_out", "deemed_let_out"]),
  donation_amount: z.number().min(0),
  education_loan_interest: z.number().min(0),
  disability_details: z.object({
    is_disabled: z.boolean(),
    type: z.enum(["normal_disability", "severe_disability"]).optional(),
  }),
  other_income: z.object({
    interest_from_savings: z.number().min(0),
    fixed_deposit_interest: z.number().min(0),
  }),
});

type TaxFormData = z.infer<typeof taxFormSchema>;

// New type for the user-facing form, including the detailed fields
type UserFacingFormData = TaxFormData & {
  ui_investments: {
    epf: number;
    ppf: number;
    lic: number;
    elss: number;
    home_loan_principal: number;
    other_80c: number;
  };
  ui_parents_age: {
    father_age?: number;
    mother_age?: number;
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
    const amount = parseFloat(deductionMatch[2].replace(/,/g, ""));
    deductions[section] = amount;
    totalDeductions += amount;
  }

  // Extract totals
  const totalsRegex =
    /\*\*Total Estimated Deductions\*\*: ₹([\d,]+)\n\*\*Total Estimated Taxable Income\*\*: ₹([\d,]+)\n\*\*Total Estimated Tax Liability\*\*: ₹([\d,]+)/;
  const totalsMatch = response.match(totalsRegex);
  if (totalsMatch) {
    totalDeductions = parseFloat(totalsMatch[1].replace(/,/g, ""));
    taxableIncome = parseFloat(totalsMatch[2].replace(/,/g, ""));
    taxLiability = parseFloat(totalsMatch[3].replace(/,/g, ""));
  }

  return {
    total_tax_liability: taxLiability,
    total_deductions: totalDeductions,
    taxable_income: taxableIncome,
    estimated_savings: totalDeductions,
    breakdown: deductions,
    rawResponse: response,
  };
};

const formatSectionName = (section: string): string => {
  return section
    .replace(/_/g, " ")
    .replace(/section/g, "Section ")
    .replace(/(^|\s)\w/g, (match) => match.toUpperCase());
};

const getDeductionDescription = (section: string): string => {
  const descriptions: Record<string, string> = {
    standard_deduction: "Standard deduction for salaried individuals",
    section_24B_deduction: "Interest on home loan for self-occupied property",
    section_80C_deduction: "Investments in PPF, ELSS, Life Insurance, etc.",
    section_80CCD1B_deduction: "Additional NPS contribution (Tier 1 account)",
    section_80D_deduction: "Health insurance premium for self/family/parents",
    section_80G_deduction: "Eligible donations to charitable institutions",
    section_80E_deduction: "Interest on education loan for higher studies",
    section_80DD_deduction: "Medical treatment of disabled dependent",
    section_80TTA_deduction: "Interest from savings accounts",
    section_80TTB_deduction: "Interest income for senior citizens",
  };

  return descriptions[section] || "Tax deduction under this section";
};

export const TaxCalculator: React.FC = () => {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [calculationResult, setCalculationResult] =
    useState<TaxCalculationResult | null>(null);
  const [isCalculating, setIsCalculating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<UserFacingFormData>({
    resolver: zodResolver(taxFormSchema),
    defaultValues: {
      salary: 0,
      user_age: 25,
      is_senior_citizen: false,
      investments: {
        "80C_investments": 0,
        nps_contribution: 0,
      },
      health_insurance_premium: 0,
      parents_health_insurance_premium: 0,
      medical_expenses: 0,
      parents_age: 0,
      housing_loan_interest: 0,
      property_status: "self_occupied",
      donation_amount: 0,
      education_loan_interest: 0,
      disability_details: {
        is_disabled: false,
        type: undefined,
      },
      other_income: {
        interest_from_savings: 0,
        fixed_deposit_interest: 0,
      },
      // Initialize new UI fields
      ui_investments: {
        epf: 0,
        ppf: 0,
        lic: 0,
        elss: 0,
        home_loan_principal: 0,
        other_80c: 0,
      },
      ui_parents_age: {
        father_age: undefined,
        mother_age: undefined,
      },
    },
  });

  const watchedValues = watch();
  const totalSteps = 5;
  const progress = (currentStep / totalSteps) * 100;

  // Effect to automatically determine senior citizen status
  useEffect(() => {
    const age = watchedValues.user_age;
    setValue("is_senior_citizen", age >= 60);
  }, [watchedValues.user_age, setValue]);

  // Effect to sum up 80C investments and update the backend-facing field
  useEffect(() => {
    const { epf, ppf, lic, elss, home_loan_principal, other_80c } =
      watchedValues.ui_investments;
    const total80C =
      (epf || 0) +
      (ppf || 0) +
      (lic || 0) +
      (elss || 0) +
      (home_loan_principal || 0) +
      (other_80c || 0);
    setValue("investments.80C_investments", total80C);
  }, [watchedValues.ui_investments, setValue]);

  // Effect to calculate average parents' age and update the backend-facing field
  useEffect(() => {
    const { father_age, mother_age } = watchedValues.ui_parents_age;
    const fAge = father_age && father_age > 0 ? father_age : null;
    const mAge = mother_age && mother_age > 0 ? mother_age : null;

    let finalAge = 0;
    if (fAge && mAge) {
      finalAge = Math.floor((fAge + mAge) / 2);
    } else if (fAge) {
      finalAge = fAge;
    } else if (mAge) {
      finalAge = mAge;
    }
    setValue("parents_age", finalAge);
  }, [watchedValues.ui_parents_age, setValue]);

  const handleCalculateTax = async (data: TaxFormData) => {
    console.log("Form submitted with data:", data);
    setIsCalculating(true);
    setError(null);

    try {
      const user = localStorage.getItem("user")
        ? JSON.parse(localStorage.getItem("user") || "{}")
        : {};
      const userId = user.id || "";

      if (!userId) {
        throw new Error("User ID is required for tax calculation");
      }

      // The request payload uses the `TaxFormData` structure, which is what the backend expects.
      // The extra UI fields are automatically excluded.
      const requestPayload = {
        user_details: {
          salary: data.salary,
          user_age: data.user_age,
          is_senior_citizen: data.is_senior_citizen,
          investments: {
            "80C_investments": data.investments["80C_investments"],
            nps_contribution: data.investments.nps_contribution,
          },
          health_insurance_premium: data.health_insurance_premium,
          parents_health_insurance_premium:
            data.parents_health_insurance_premium,
          medical_expenses: data.medical_expenses,
          parents_age: data.parents_age,
          housing_loan_interest: data.housing_loan_interest,
          property_status: data.property_status,
          donation_amount: data.donation_amount,
          education_loan_interest: data.education_loan_interest,
          disability_details: {
            is_disabled: data.disability_details.is_disabled,
            type: data.disability_details.type || null,
          },
          other_income: {
            interest_from_savings: data.other_income.interest_from_savings,
            fixed_deposit_interest: data.other_income.fixed_deposit_interest,
          },
        },
      };

      console.log("Sending payload:", requestPayload);

      const response = await fetch(
        "http://localhost:8000/chats/start_new_tax_session",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-User-ID": userId,
          },
          body: JSON.stringify(requestPayload),
        }
      );

      console.log("Response status:", response.status);

      if (!response.ok) {
        const errorData = await response.json();
        console.error("API Error Response:", errorData);
        throw new Error(errorData.message || "Tax calculation failed");
      }

      const responseData = await response.json();
      console.log("API Response:", responseData);

      // Redirect to chat session page with session_id
      if (responseData.session_id) {
        localStorage.setItem("session_id", responseData.session_id);
        navigate(`/chat?session_id=${responseData.session_id}`);
        return;
      }

      const result = parseTaxResponse(
        responseData.initial_bot_response || responseData.bot_response
      );
      setCalculationResult(result);
      setCurrentStep(6);
    } catch (err) {
      console.error("Error in handleCalculateTax:", err);
      const errorMessage =
        err instanceof Error ? err.message : "Tax calculation failed";
      setError(errorMessage);
    } finally {
      setIsCalculating(false);
    }
  };

  const nextStep = () =>
    currentStep < totalSteps && setCurrentStep(currentStep + 1);
  const prevStep = () => currentStep > 1 && setCurrentStep(currentStep - 1);

  const renderStep = () => {
    switch (currentStep) {
      case 1:
        return (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="h-5 w-5 text-green-600" />
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
                    {...register("salary", { valueAsNumber: true })}
                  />
                  {errors.salary && (
                    <p className="text-sm text-red-500">
                      {errors.salary.message}
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="user_age">Your Age</Label>
                  <Input
                    id="user_age"
                    type="number"
                    placeholder="e.g., 35"
                    {...register("user_age", { valueAsNumber: true })}
                  />
                  {errors.user_age && (
                    <p className="text-sm text-red-500">
                      {errors.user_age.message}
                    </p>
                  )}
                </div>
              </div>

              <div className="flex items-center justify-between p-4 border rounded-lg bg-blue-50">
                <div>
                  <h4 className="font-medium">Taxpayer Status</h4>
                  <p className="text-sm text-gray-600">
                    {watchedValues.is_senior_citizen
                      ? "You qualify for senior citizen benefits (60+ years)."
                      : "You are classified as a regular taxpayer."}
                  </p>
                </div>
                <Badge
                  variant={
                    watchedValues.is_senior_citizen ? "default" : "secondary"
                  }
                >
                  {watchedValues.is_senior_citizen
                    ? "Senior Citizen"
                    : "Regular"}
                </Badge>
              </div>
            </CardContent>
          </Card>
        );

      case 2:
        const total80CInvestments =
          watchedValues.investments?.["80C_investments"] || 0;
        const is80CLimitReached = total80CInvestments >= 150000;

        return (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <PiggyBank className="h-5 w-5 text-blue-600" />
                Investments & Savings
              </CardTitle>
              <CardDescription>
                Provide a breakdown of your tax-saving investments.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* --- NEW 80C Detailed Section --- */}
              <div className="p-4 border rounded-lg space-y-4">
                <h4 className="font-medium">
                  Section 80C Investments Breakdown
                </h4>
                <p className="text-xs text-gray-500">
                  Enter your investments below. The total is capped at
                  ₹1,50,000.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="ui_investments.epf">
                      EPF Contribution (₹)
                    </Label>
                    <Input
                      id="ui_investments.epf"
                      type="number"
                      {...register("ui_investments.epf", {
                        valueAsNumber: true,
                      })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="ui_investments.ppf">
                      PPF Contribution (₹)
                    </Label>
                    <Input
                      id="ui_investments.ppf"
                      type="number"
                      {...register("ui_investments.ppf", {
                        valueAsNumber: true,
                      })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="ui_investments.lic">
                      Life Insurance Premium (₹)
                    </Label>
                    <Input
                      id="ui_investments.lic"
                      type="number"
                      {...register("ui_investments.lic", {
                        valueAsNumber: true,
                      })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="ui_investments.elss">
                      ELSS / Mutual Funds (₹)
                    </Label>
                    <Input
                      id="ui_investments.elss"
                      type="number"
                      {...register("ui_investments.elss", {
                        valueAsNumber: true,
                      })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="ui_investments.home_loan_principal">
                      Home Loan Principal (₹)
                    </Label>
                    <Input
                      id="ui_investments.home_loan_principal"
                      type="number"
                      {...register("ui_investments.home_loan_principal", {
                        valueAsNumber: true,
                      })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="ui_investments.other_80c">
                      Other 80C (e.g., NSC) (₹)
                    </Label>
                    <Input
                      id="ui_investments.other_80c"
                      type="number"
                      {...register("ui_investments.other_80c", {
                        valueAsNumber: true,
                      })}
                    />
                  </div>
                </div>
                <Separator className="my-4" />
                <div className="p-3 bg-gray-50 rounded-lg">
                  <div className="flex justify-between items-center mb-2">
                    <h5 className="font-semibold">Total 80C Contribution</h5>
                    <Badge
                      variant={is80CLimitReached ? "destructive" : "default"}
                    >
                      ₹{total80CInvestments.toLocaleString()} / ₹1,50,000
                    </Badge>
                  </div>
                  <Progress
                    value={(total80CInvestments / 150000) * 100}
                    className="h-2"
                  />
                  {errors.investments?.["80C_investments"] && (
                    <p className="text-sm text-red-500 mt-2">
                      {errors.investments["80C_investments"].message}
                    </p>
                  )}
                </div>
              </div>
              {/* --- End of 80C Section --- */}

              <div className="space-y-2">
                <Label htmlFor="nps_contribution">
                  NPS Contribution (Section 80CCD(1B)) (₹)
                </Label>
                <Input
                  id="nps_contribution"
                  type="number"
                  placeholder="e.g., 50000"
                  {...register("investments.nps_contribution", {
                    valueAsNumber: true,
                  })}
                />
                <p className="text-xs text-gray-500">
                  Additional deduction over and above 80C limit (Max: ₹50,000)
                </p>
                {errors.investments?.nps_contribution && (
                  <p className="text-sm text-red-500">
                    {errors.investments.nps_contribution.message}
                  </p>
                )}
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
                Health insurance and medical expense details for you and your
                family.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label htmlFor="health_insurance_premium">
                    Health Insurance Premium (₹)
                  </Label>
                  <Input
                    id="health_insurance_premium"
                    type="number"
                    placeholder="e.g., 18000"
                    {...register("health_insurance_premium", {
                      valueAsNumber: true,
                    })}
                  />
                  <p className="text-xs text-gray-500">
                    For self, spouse, and children.
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="parents_health_insurance_premium">
                    Parents' Health Insurance (₹)
                  </Label>
                  <Input
                    id="parents_health_insurance_premium"
                    type="number"
                    placeholder="e.g., 30000"
                    {...register("parents_health_insurance_premium", {
                      valueAsNumber: true,
                    })}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="medical_expenses">
                    Preventive Health Checkup (₹)
                  </Label>
                  <Input
                    id="medical_expenses"
                    type="number"
                    placeholder="e.g., 5000"
                    {...register("medical_expenses", { valueAsNumber: true })}
                  />
                  <p className="text-xs text-gray-500">
                    Capped at ₹5,000 (part of 80D limit). For senior citizens,
                    this covers general medical expenses.
                  </p>
                </div>

                {/* --- NEW Parents' Age Section --- */}
                <div className="space-y-2 md:col-span-2">
                  <Label>Parents' Age (Optional)</Label>
                  <div className="grid grid-cols-2 gap-4 p-4 border rounded-lg">
                    <div className="space-y-2">
                      <Label htmlFor="father_age">Father's Age</Label>
                      <Input
                        id="father_age"
                        type="number"
                        placeholder="e.g., 65"
                        {...register("ui_parents_age.father_age", {
                          valueAsNumber: true,
                        })}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="mother_age">Mother's Age</Label>
                      <Input
                        id="mother_age"
                        type="number"
                        placeholder="e.g., 62"
                        {...register("ui_parents_age.mother_age", {
                          valueAsNumber: true,
                        })}
                      />
                    </div>
                  </div>
                  <p className="text-xs text-gray-500">
                    Enter if you pay their health premium. This helps determine
                    senior citizen benefits for them.
                  </p>
                </div>
                {/* --- End of Parents' Age Section --- */}
              </div>

              <div className="space-y-4">
                <h4 className="font-medium">
                  Disability Details (Section 80DD)
                </h4>
                <div className="flex items-center justify-between p-4 border rounded-lg">
                  <div>
                    <Label htmlFor="is_disabled">
                      Do you support a dependent with a disability?
                    </Label>
                  </div>
                  <Switch
                    id="is_disabled"
                    checked={watchedValues.disability_details?.is_disabled}
                    onCheckedChange={(checked) =>
                      setValue("disability_details.is_disabled", checked)
                    }
                  />
                </div>

                {watchedValues.disability_details?.is_disabled && (
                  <div className="space-y-2">
                    <Label htmlFor="disability_type">Disability Type</Label>
                    <Select
                      value={watchedValues.disability_details.type}
                      onValueChange={(value) =>
                        setValue(
                          "disability_details.type",
                          value as "normal_disability" | "severe_disability"
                        )
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select disability type" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="normal_disability">
                          Normal Disability (40-80%)
                        </SelectItem>
                        <SelectItem value="severe_disability">
                          Severe Disability (80%+)
                        </SelectItem>
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
                  <Label htmlFor="housing_loan_interest">
                    Housing Loan Interest (₹)
                  </Label>
                  <Input
                    id="housing_loan_interest"
                    type="number"
                    placeholder="e.g., 200000"
                    {...register("housing_loan_interest", {
                      valueAsNumber: true,
                    })}
                  />
                  <p className="text-xs text-gray-500">
                    Section 24(b) - Interest on housing loan.
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="property_status">Property Status</Label>
                  <Select
                    value={watchedValues.property_status}
                    onValueChange={(value) =>
                      setValue(
                        "property_status",
                        value as "self_occupied" | "let_out" | "deemed_let_out"
                      )
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="self_occupied">
                        Self Occupied
                      </SelectItem>
                      <SelectItem value="let_out">Let Out</SelectItem>
                      <SelectItem value="deemed_let_out">
                        Deemed Let Out
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="education_loan_interest">
                    Education Loan Interest (₹)
                  </Label>
                  <Input
                    id="education_loan_interest"
                    type="number"
                    placeholder="e.g., 45000"
                    {...register("education_loan_interest", {
                      valueAsNumber: true,
                    })}
                  />
                  <p className="text-xs text-gray-500">
                    Section 80E - No upper limit on deduction for 8 years.
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="donation_amount">
                    Eligible Donations (₹)
                  </Label>
                  <Input
                    id="donation_amount"
                    type="number"
                    placeholder="e.g., 5000"
                    {...register("donation_amount", { valueAsNumber: true })}
                  />
                  <p className="text-xs text-gray-500">
                    Section 80G - Donations to specified funds/charities.
                  </p>
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
                  <Label htmlFor="interest_from_savings">
                    Savings Account Interest (₹)
                  </Label>
                  <Input
                    id="interest_from_savings"
                    type="number"
                    placeholder="e.g., 8000"
                    {...register("other_income.interest_from_savings", {
                      valueAsNumber: true,
                    })}
                  />
                  <p className="text-xs text-gray-500">
                    Deductible up to ₹10,000 under Section 80TTA.
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="fixed_deposit_interest">
                    Fixed Deposit Interest (₹)
                  </Label>
                  <Input
                    id="fixed_deposit_interest"
                    type="number"
                    placeholder="e.g., 30000"
                    {...register("other_income.fixed_deposit_interest", {
                      valueAsNumber: true,
                    })}
                  />
                  <p className="text-xs text-gray-500">
                    Fully taxable. Senior citizens can claim deduction under
                    80TTB.
                  </p>
                </div>
              </div>

              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>Interest Income Deduction</AlertTitle>
                <AlertDescription>
                  {watchedValues.is_senior_citizen
                    ? "As a senior citizen, you can claim a deduction up to ₹50,000 for total interest income (savings & FD) under Section 80TTB."
                    : "You can claim a deduction up to ₹10,000 for savings account interest under Section 80TTA."}
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
                  <h4 className="font-medium text-blue-800 mb-2">
                    Total Deductions
                  </h4>
                  <p className="text-2xl font-bold text-blue-600">
                    ₹{calculationResult.total_deductions.toLocaleString()}
                  </p>
                </div>

                <div className="p-4 bg-green-50 rounded-lg border border-green-100">
                  <h4 className="font-medium text-green-800 mb-2">
                    Taxable Income
                  </h4>
                  <p className="text-2xl font-bold text-green-600">
                    ₹{calculationResult.taxable_income.toLocaleString()}
                  </p>
                </div>

                <div className="p-4 bg-orange-50 rounded-lg border border-orange-100">
                  <h4 className="font-medium text-orange-800 mb-2">
                    Tax Liability
                  </h4>
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
                          <Badge
                            variant="outline"
                            className="bg-green-50 text-green-700 px-3 py-1"
                          >
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
                  <li>This calculation is based on the old tax regime.</li>
                  <li>
                    A standard deduction of ₹50,000 has been included in the
                    calculation.
                  </li>
                  <li>
                    Tax laws are subject to change. Please consult a
                    professional for financial advice.
                  </li>
                </ul>
              </div>

              {/* Chat CTA */}
              <div className="mt-6 text-center">
                <p className="mb-2 text-gray-700">
                  Have questions or want to explore more optimization
                  strategies?
                </p>
                <Button onClick={() => navigate("/chat")}>
                  <MessageSquare className="mr-2 h-4 w-4" />
                  Chat with Tax Advisor
                </Button>
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

  const stepTitles = [
    "Basic Information",
    "Investments & Savings",
    "Health & Medical",
    "Loans & Donations",
    "Other Income",
  ];

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">Tax Calculator</CardTitle>
          <CardDescription>
            Fill in your financial details to calculate your tax liability and
            discover potential savings.
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
            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold">
                    Tax Information Form
                  </h2>
                  <Badge variant="outline">
                    Step {currentStep > totalSteps ? totalSteps : currentStep}{" "}
                    of {totalSteps}
                  </Badge>
                </div>
                <Progress value={progress} className="h-2" />
                <p className="text-sm text-gray-600 mt-2">
                  {currentStep > totalSteps
                    ? "Calculation Complete"
                    : `Step ${currentStep}: ${stepTitles[currentStep - 1]}`}
                </p>
              </CardContent>
            </Card>

            <form onSubmit={handleSubmit(handleCalculateTax)}>
              {renderStep()}
              <div className="flex justify-between mt-6">
                <Button
                  type="button"
                  variant="outline"
                  onClick={prevStep}
                  disabled={currentStep === 1 || currentStep > totalSteps}
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
                    <Button type="submit" disabled={isCalculating}>
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
