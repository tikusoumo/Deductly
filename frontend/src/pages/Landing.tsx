import React from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Link } from 'react-router-dom';
import { Calculator, MessageCircle, FileText, TrendingUp, Shield, Clock } from 'lucide-react';

export const Landing: React.FC = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-md">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Calculator className="h-8 w-8 text-blue-600" />
            <span className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-green-600 bg-clip-text text-transparent">
              TaxSaver AI
            </span>
          </div>
          <div className="flex items-center space-x-4">
            <Link to="/login">
              <Button variant="ghost">Sign In</Button>
            </Link>
            <Link to="/signup">
              <Button>Get Started</Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-16 text-center">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-5xl font-bold text-gray-900 mb-6">
            Maximize Your Tax Savings with{' '}
            <span className="bg-gradient-to-r from-blue-600 to-green-600 bg-clip-text text-transparent">
              AI-Powered Guidance
            </span>
          </h1>
          <p className="text-xl text-gray-600 mb-8 leading-relaxed">
            Get personalized tax advice, discover hidden deductions, and optimize your tax strategy 
            with our advanced RAG AI system trained on the latest tax laws and regulations.
          </p>
          <div className="flex justify-center gap-4">
            <Link to="/signup">
              <Button size="lg" className="px-8 py-3 text-lg">
                Start Free Consultation
              </Button>
            </Link>
            <Link to="/login">
              <Button variant="outline" size="lg" className="px-8 py-3 text-lg">
                Sign In
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="container mx-auto px-4 py-16">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">
            Everything You Need for Tax Success
          </h2>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Our comprehensive AI-powered platform helps you navigate complex tax situations 
            and maximize your savings year-round.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          <Card className="group hover:shadow-lg transition-all duration-300 border-0 bg-white/60 backdrop-blur-sm">
            <CardHeader>
              <div className="h-12 w-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4 group-hover:bg-blue-200 transition-colors">
                <MessageCircle className="h-6 w-6 text-blue-600" />
              </div>
              <CardTitle>AI Tax Advisor</CardTitle>
              <CardDescription>
                Chat with our intelligent AI to get instant answers about tax deductions, 
                filing requirements, and optimization strategies.
              </CardDescription>
            </CardHeader>
          </Card>

          <Card className="group hover:shadow-lg transition-all duration-300 border-0 bg-white/60 backdrop-blur-sm">
            <CardHeader>
              <div className="h-12 w-12 bg-green-100 rounded-lg flex items-center justify-center mb-4 group-hover:bg-green-200 transition-colors">
                <FileText className="h-6 w-6 text-green-600" />
              </div>
              <CardTitle>Smart Document Processing</CardTitle>
              <CardDescription>
                Upload your tax documents and let our AI analyze them to identify 
                potential deductions and savings opportunities.
              </CardDescription>
            </CardHeader>
          </Card>

          <Card className="group hover:shadow-lg transition-all duration-300 border-0 bg-white/60 backdrop-blur-sm">
            <CardHeader>
              <div className="h-12 w-12 bg-orange-100 rounded-lg flex items-center justify-center mb-4 group-hover:bg-orange-200 transition-colors">
                <TrendingUp className="h-6 w-6 text-orange-600" />
              </div>
              <CardTitle>Savings Optimization</CardTitle>
              <CardDescription>
                Get personalized recommendations to maximize your tax savings 
                based on your unique financial situation.
              </CardDescription>
            </CardHeader>
          </Card>

          <Card className="group hover:shadow-lg transition-all duration-300 border-0 bg-white/60 backdrop-blur-sm">
            <CardHeader>
              <div className="h-12 w-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4 group-hover:bg-purple-200 transition-colors">
                <Shield className="h-6 w-6 text-purple-600" />
              </div>
              <CardTitle>Secure & Compliant</CardTitle>
              <CardDescription>
                Your data is protected with bank-level security. All advice 
                complies with current tax laws and regulations.
              </CardDescription>
            </CardHeader>
          </Card>

          <Card className="group hover:shadow-lg transition-all duration-300 border-0 bg-white/60 backdrop-blur-sm">
            <CardHeader>
              <div className="h-12 w-12 bg-red-100 rounded-lg flex items-center justify-center mb-4 group-hover:bg-red-200 transition-colors">
                <Clock className="h-6 w-6 text-red-600" />
              </div>
              <CardTitle>Year-Round Support</CardTitle>
              <CardDescription>
                Get tax guidance whenever you need it, not just during tax season. 
                Plan ahead and make informed financial decisions.
              </CardDescription>
            </CardHeader>
          </Card>

          <Card className="group hover:shadow-lg transition-all duration-300 border-0 bg-white/60 backdrop-blur-sm">
            <CardHeader>
              <div className="h-12 w-12 bg-teal-100 rounded-lg flex items-center justify-center mb-4 group-hover:bg-teal-200 transition-colors">
                <Calculator className="h-6 w-6 text-teal-600" />
              </div>
              <CardTitle>Easy Tax Submission</CardTitle>
              <CardDescription>
                Streamline your tax filing process with our integrated submission 
                system and real-time status tracking.
              </CardDescription>
            </CardHeader>
          </Card>
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-gradient-to-r from-blue-600 to-green-600 py-16">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            Ready to Maximize Your Tax Savings?
          </h2>
          <p className="text-xl text-blue-100 mb-8 max-w-2xl mx-auto">
            Join thousands of users who have already discovered hidden deductions 
            and optimized their tax strategies with TaxSaver AI.
          </p>
          <Link to="/signup">
            <Button size="lg" variant="secondary" className="px-8 py-3 text-lg">
              Start Your Free Consultation
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-8">
        <div className="container mx-auto px-4 text-center">
          <div className="flex items-center justify-center space-x-2 mb-4">
            <Calculator className="h-6 w-6 text-blue-400" />
            <span className="text-xl font-bold">TaxSaver AI</span>
          </div>
          <p className="text-gray-400">
            © 2024 TaxSaver AI. All rights reserved. | Privacy Policy | Terms of Service
          </p>
        </div>
      </footer>
    </div>
  );
};