import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  MessageCircle, 
  FileText, 
  Search, 
  Calendar,
  DollarSign,
  TrendingUp,
  Filter
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface HistoryItem {
  id: string;
  type: 'chat' | 'submission';
  title: string;
  description: string;
  date: string;
  status: string;
  savings?: number;
  tags: string[];
}

export const History: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [filterType, setFilterType] = useState('all');

  const historyItems: HistoryItem[] = [
    {
      id: '1',
      type: 'chat',
      title: 'Home Office Deduction Consultation',
      description: 'Discussed home office setup and calculated potential deductions based on 200 sq ft workspace.',
      date: '2024-01-15T10:30:00Z',
      status: 'completed',
      savings: 1200,
      tags: ['home office', 'deductions', 'workspace']
    },
    {
      id: '2',
      type: 'submission',
      title: '2024 Personal Tax Return',
      description: 'Submitted W-2, 1099 forms, and medical expense receipts for comprehensive tax analysis.',
      date: '2024-01-14T14:20:00Z',
      status: 'processing',
      savings: 2847,
      tags: ['tax return', 'w-2', 'medical expenses']
    },
    {
      id: '3',
      type: 'chat',
      title: 'Medical Expense Deduction Analysis',
      description: 'Analyzed medical expenses and determined eligibility for itemized deductions.',
      date: '2024-01-12T09:15:00Z',
      status: 'completed',
      savings: 856,
      tags: ['medical', 'expenses', 'itemized']
    },
    {
      id: '4',
      type: 'submission',
      title: 'Business Travel Expense Documentation',
      description: 'Uploaded mileage logs and travel receipts for business deduction calculations.',
      date: '2024-01-10T16:45:00Z',
      status: 'completed',
      savings: 634,
      tags: ['business', 'travel', 'mileage']
    },
    {
      id: '5',
      type: 'chat',
      title: 'Charitable Donation Optimization',
      description: 'Discussed strategies for maximizing charitable donation deductions and timing.',
      date: '2024-01-08T11:30:00Z',
      status: 'completed',
      savings: 423,
      tags: ['charitable', 'donations', 'strategy']
    },
    {
      id: '6',
      type: 'submission',
      title: 'Quarterly Business Expenses',
      description: 'Submitted Q4 2023 business expense receipts and invoices for analysis.',
      date: '2024-01-05T13:20:00Z',
      status: 'completed',
      savings: 1789,
      tags: ['business', 'quarterly', 'expenses']
    }
  ];

  const filteredItems = historyItems.filter(item => {
    const matchesSearch = item.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         item.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         item.tags.some(tag => tag.toLowerCase().includes(searchTerm.toLowerCase()));
    
    const matchesStatus = filterStatus === 'all' || item.status === filterStatus;
    const matchesType = filterType === 'all' || item.type === filterType;
    
    return matchesSearch && matchesStatus && matchesType;
  });

  const totalSavings = historyItems.reduce((sum, item) => sum + (item.savings || 0), 0);
  const completedItems = historyItems.filter(item => item.status === 'completed').length;
  const chatSessions = historyItems.filter(item => item.type === 'chat').length;
  const submissions = historyItems.filter(item => item.type === 'submission').length;

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'processing':
        return 'bg-yellow-100 text-yellow-800';
      case 'draft':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-blue-100 text-blue-800';
    }
  };

  const getTypeIcon = (type: string) => {
    return type === 'chat' ? MessageCircle : FileText;
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">History</h1>
          <p className="text-gray-600 mt-1">View your tax consultation and submission history.</p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <DollarSign className="h-5 w-5 text-green-600" />
              <div>
                <p className="text-sm text-gray-600">Total Savings</p>
                <p className="text-xl font-bold text-green-600">${totalSavings.toLocaleString()}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <TrendingUp className="h-5 w-5 text-blue-600" />
              <div>
                <p className="text-sm text-gray-600">Completed</p>
                <p className="text-xl font-bold text-blue-600">{completedItems}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <MessageCircle className="h-5 w-5 text-purple-600" />
              <div>
                <p className="text-sm text-gray-600">Chat Sessions</p>
                <p className="text-xl font-bold text-purple-600">{chatSessions}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <FileText className="h-5 w-5 text-orange-600" />
              <div>
                <p className="text-sm text-gray-600">Submissions</p>
                <p className="text-xl font-bold text-orange-600">{submissions}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="h-5 w-5" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Search</label>
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="Search history..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <label className="text-sm font-medium">Status</label>
              <Select value={filterStatus} onValueChange={setFilterStatus}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Statuses</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="processing">Processing</SelectItem>
                  <SelectItem value="draft">Draft</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <label className="text-sm font-medium">Type</label>
              <Select value={filterType} onValueChange={setFilterType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Types</SelectItem>
                  <SelectItem value="chat">Chat Sessions</SelectItem>
                  <SelectItem value="submission">Submissions</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* History Items */}
      <Tabs defaultValue="all" className="space-y-4">
        <TabsList>
          <TabsTrigger value="all">All History</TabsTrigger>
          <TabsTrigger value="chat">Chat Sessions</TabsTrigger>
          <TabsTrigger value="submission">Submissions</TabsTrigger>
        </TabsList>
        
        <TabsContent value="all" className="space-y-4">
          {filteredItems.map((item) => {
            const Icon = getTypeIcon(item.type);
            return (
              <Card key={item.id} className="hover:shadow-md transition-shadow">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start space-x-4 flex-1">
                      <div className="flex-shrink-0">
                        <Icon className={`h-6 w-6 ${item.type === 'chat' ? 'text-blue-600' : 'text-green-600'}`} />
                      </div>
                      
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2 mb-2">
                          <h3 className="text-lg font-medium text-gray-900">{item.title}</h3>
                          <Badge className={getStatusColor(item.status)}>
                            {item.status}
                          </Badge>
                        </div>
                        
                        <p className="text-gray-600 mb-3">{item.description}</p>
                        
                        <div className="flex items-center space-x-4 text-sm text-gray-500">
                          <div className="flex items-center space-x-1">
                            <Calendar className="h-4 w-4" />
                            <span>{formatDistanceToNow(new Date(item.date), { addSuffix: true })}</span>
                          </div>
                          
                          {item.savings && (
                            <div className="flex items-center space-x-1 text-green-600">
                              <DollarSign className="h-4 w-4" />
                              <span>${item.savings.toLocaleString()} saved</span>
                            </div>
                          )}
                        </div>
                        
                        <div className="flex flex-wrap gap-1 mt-3">
                          {item.tags.map((tag, index) => (
                            <Badge key={index} variant="outline" className="text-xs">
                              {tag}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    </div>
                    
                    <Button variant="ghost" size="sm">
                      View Details
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </TabsContent>
        
        <TabsContent value="chat" className="space-y-4">
          {filteredItems.filter(item => item.type === 'chat').map((item) => (
            <Card key={item.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-4 flex-1">
                    <MessageCircle className="h-6 w-6 text-blue-600 flex-shrink-0" />
                    <div className="flex-1">
                      <h3 className="text-lg font-medium text-gray-900 mb-2">{item.title}</h3>
                      <p className="text-gray-600 mb-3">{item.description}</p>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-500">
                          {formatDistanceToNow(new Date(item.date), { addSuffix: true })}
                        </span>
                        {item.savings && (
                          <span className="text-sm text-green-600 font-medium">
                            ${item.savings.toLocaleString()} saved
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <Button variant="ghost" size="sm">
                    View Chat
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </TabsContent>
        
        <TabsContent value="submission" className="space-y-4">
          {filteredItems.filter(item => item.type === 'submission').map((item) => (
            <Card key={item.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-4 flex-1">
                    <FileText className="h-6 w-6 text-green-600 flex-shrink-0" />
                    <div className="flex-1">
                      <h3 className="text-lg font-medium text-gray-900 mb-2">{item.title}</h3>
                      <p className="text-gray-600 mb-3">{item.description}</p>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-500">
                          {formatDistanceToNow(new Date(item.date), { addSuffix: true })}
                        </span>
                        {item.savings && (
                          <span className="text-sm text-green-600 font-medium">
                            ${item.savings.toLocaleString()} saved
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <Button variant="ghost" size="sm">
                    View Submission
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </TabsContent>
      </Tabs>
    </div>
  );
};