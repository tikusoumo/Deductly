import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { 
  Upload, 
  FileText, 
  CheckCircle, 
  Clock, 
  AlertCircle,
  DollarSign,
  Calendar,
  Download
} from 'lucide-react';
import { TaxSubmission } from '@/types';

export const Submissions: React.FC = () => {
  const [submissions, setSubmissions] = useState<TaxSubmission[]>([
    {
      id: '1',
      title: '2024 Personal Tax Return',
      status: 'processing',
      submittedAt: '2024-01-15T10:30:00Z',
      documents: ['W-2', 'Form 1099-INT', 'Medical Receipts'],
      estimatedSavings: 2847
    },
    {
      id: '2',
      title: 'Q4 2023 Business Expenses',
      status: 'completed',
      submittedAt: '2024-01-10T14:20:00Z',
      documents: ['Business Receipts', 'Mileage Log', 'Home Office'],
      estimatedSavings: 1456
    },
    {
      id: '3',
      title: 'Medical Deduction Package',
      status: 'draft',
      documents: ['Medical Bills', 'Insurance Statements'],
      estimatedSavings: 892
    }
  ]);

  const [isUploading, setIsUploading] = useState(false);
  const [newSubmission, setNewSubmission] = useState({
    title: '',
    description: '',
    files: [] as File[]
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsUploading(true);

    // Mock submission process
    setTimeout(() => {
      const submission: TaxSubmission = {
        id: Date.now().toString(),
        title: newSubmission.title,
        status: 'submitted',
        submittedAt: new Date().toISOString(),
        documents: newSubmission.files.map(f => f.name),
        estimatedSavings: Math.floor(Math.random() * 3000) + 500
      };

      setSubmissions(prev => [submission, ...prev]);
      setNewSubmission({ title: '', description: '', files: [] });
      setIsUploading(false);
    }, 2000);
  };

  const getStatusIcon = (status: TaxSubmission['status']) => {
    switch (status) {
      case 'draft':
        return <FileText className="h-4 w-4" />;
      case 'submitted':
        return <Upload className="h-4 w-4" />;
      case 'processing':
        return <Clock className="h-4 w-4" />;
      case 'completed':
        return <CheckCircle className="h-4 w-4" />;
      default:
        return <AlertCircle className="h-4 w-4" />;
    }
  };

  const getStatusColor = (status: TaxSubmission['status']) => {
    switch (status) {
      case 'draft':
        return 'bg-gray-100 text-gray-800';
      case 'submitted':
        return 'bg-blue-100 text-blue-800';
      case 'processing':
        return 'bg-yellow-100 text-yellow-800';
      case 'completed':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-red-100 text-red-800';
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Tax Submissions</h1>
          <p className="text-gray-600 mt-1">Submit and track your tax documents and returns.</p>
        </div>
      </div>

      {/* New Submission Form */}
      <Card>
        <CardHeader>
          <CardTitle>Submit New Tax Documents</CardTitle>
          <CardDescription>
            Upload your tax documents for AI analysis and optimization
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="title">Submission Title</Label>
                <Input
                  id="title"
                  placeholder="e.g., 2024 Personal Tax Return"
                  value={newSubmission.title}
                  onChange={(e) => setNewSubmission(prev => ({ ...prev, title: e.target.value }))}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="files">Documents</Label>
                <Input
                  id="files"
                  type="file"
                  multiple
                  accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
                  onChange={(e) => setNewSubmission(prev => ({ 
                    ...prev, 
                    files: Array.from(e.target.files || []) 
                  }))}
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="description">Description (Optional)</Label>
              <Textarea
                id="description"
                placeholder="Add any additional context or specific questions about your tax situation..."
                value={newSubmission.description}
                onChange={(e) => setNewSubmission(prev => ({ ...prev, description: e.target.value }))}
                rows={3}
              />
            </div>

            {newSubmission.files.length > 0 && (
              <div className="space-y-2">
                <Label>Selected Files</Label>
                <div className="space-y-1">
                  {newSubmission.files.map((file, index) => (
                    <div key={index} className="flex items-center space-x-2 text-sm">
                      <FileText className="h-4 w-4 text-gray-500" />
                      <span>{file.name}</span>
                      <span className="text-gray-500">({(file.size / 1024 / 1024).toFixed(2)} MB)</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <Button type="submit" disabled={!newSubmission.title || isUploading}>
              {isUploading ? (
                <>
                  <Clock className="mr-2 h-4 w-4 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Upload className="mr-2 h-4 w-4" />
                  Submit Documents
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Submissions List */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Your Submissions</h2>
        
        {submissions.map((submission) => (
          <Card key={submission.id} className="hover:shadow-md transition-shadow">
            <CardContent className="p-6">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-2 mb-2">
                    <h3 className="text-lg font-medium">{submission.title}</h3>
                    <Badge className={getStatusColor(submission.status)}>
                      {getStatusIcon(submission.status)}
                      <span className="ml-1 capitalize">{submission.status}</span>
                    </Badge>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
                    <div className="flex items-center space-x-2">
                      <Calendar className="h-4 w-4 text-gray-500" />
                      <span className="text-sm text-gray-600">
                        {submission.submittedAt 
                          ? new Date(submission.submittedAt).toLocaleDateString()
                          : 'Not submitted'
                        }
                      </span>
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      <FileText className="h-4 w-4 text-gray-500" />
                      <span className="text-sm text-gray-600">
                        {submission.documents.length} documents
                      </span>
                    </div>
                    
                    {submission.estimatedSavings && (
                      <div className="flex items-center space-x-2">
                        <DollarSign className="h-4 w-4 text-green-500" />
                        <span className="text-sm font-medium text-green-600">
                          ${submission.estimatedSavings.toLocaleString()} potential savings
                        </span>
                      </div>
                    )}
                  </div>

                  <div className="mt-4">
                    <div className="flex items-center justify-between text-sm mb-2">
                      <span className="text-gray-600">Documents:</span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {submission.documents.map((doc, index) => (
                        <Badge key={index} variant="outline" className="text-xs">
                          {doc}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  {submission.status === 'processing' && (
                    <div className="mt-4">
                      <div className="flex items-center justify-between text-sm mb-2">
                        <span className="text-gray-600">Processing Progress</span>
                        <span className="text-gray-600">75%</span>
                      </div>
                      <Progress value={75} className="h-2" />
                    </div>
                  )}
                </div>

                <div className="flex flex-col space-y-2">
                  {submission.status === 'completed' && (
                    <Button variant="outline" size="sm">
                      <Download className="mr-2 h-4 w-4" />
                      Download
                    </Button>
                  )}
                  <Button variant="ghost" size="sm">
                    View Details
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};