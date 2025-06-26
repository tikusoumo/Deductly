import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { useNavigate } from 'react-router-dom';
import { 
  MessageCircle, 
  FileText, 
  TrendingUp, 
  Clock, 
  DollarSign, 
  CheckCircle,
  Plus,
  Calculator
} from 'lucide-react';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();

  const stats = [
    {
      title: 'Potential Savings',
      value: '$3,247',
      change: '+12%',
      icon: DollarSign,
      color: 'text-green-600'
    },
    {
      title: 'Active Sessions',
      value: '3',
      change: '+1',
      icon: MessageCircle,
      color: 'text-blue-600'
    },
    {
      title: 'Documents Reviewed',
      value: '12',
      change: '+5',
      icon: FileText,
      color: 'text-purple-600'
    },
    {
      title: 'Deductions Found',
      value: '8',
      change: '+2',
      icon: TrendingUp,
      color: 'text-orange-600'
    }
  ];

  const recentSessions = [
    {
      id: '1',
      title: 'Home Office Deductions',
      status: 'active',
      lastMessage: 'Based on your 200 sq ft home office...',
      timestamp: '2 hours ago'
    },
    {
      id: '2',
      title: 'Medical Expenses',
      status: 'completed',
      lastMessage: 'Your medical expenses qualify for...',
      timestamp: '1 day ago'
    },
    {
      id: '3',
      title: 'Business Travel',
      status: 'active',
      lastMessage: 'Let me help you calculate mileage...',
      timestamp: '2 days ago'
    }
  ];

  const quickActions = [
    {
      title: 'Calculate Tax Savings',
      description: 'Use our comprehensive tax calculator',
      icon: Calculator,
      action: () => navigate('/calculator')
    },
    {
      title: 'Start New Tax Session',
      description: 'Get personalized tax advice',
      icon: MessageCircle,
      action: () => navigate('/chat')
    },
    {
      title: 'Upload Documents',
      description: 'Analyze your tax documents',
      icon: FileText,
      action: () => navigate('/submissions')
    }
  ];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-1">Welcome back! Here's your tax optimization overview.</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => navigate('/calculator')} variant="outline">
            <Calculator className="mr-2 h-4 w-4" />
            Tax Calculator
          </Button>
          <Button onClick={() => navigate('/chat')}>
            <Plus className="mr-2 h-4 w-4" />
            New Consultation
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, index) => (
          <Card key={index} className="relative overflow-hidden">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">
                {stat.title}
              </CardTitle>
              <stat.icon className={`h-4 w-4 ${stat.color}`} />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
              <p className="text-xs text-muted-foreground">
                <span className="text-green-600">{stat.change}</span> from last month
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Activity */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Recent Sessions</CardTitle>
              <CardDescription>
                Your latest tax consultation sessions
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {recentSessions.map((session) => (
                  <div key={session.id} className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 transition-colors cursor-pointer">
                    <div className="flex items-center space-x-4">
                      <div className="flex-shrink-0">
                        <MessageCircle className="h-8 w-8 text-blue-600" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {session.title}
                        </p>
                        <p className="text-sm text-gray-500 truncate">
                          {session.lastMessage}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Badge variant={session.status === 'active' ? 'default' : 'secondary'}>
                        {session.status === 'active' ? (
                          <Clock className="mr-1 h-3 w-3" />
                        ) : (
                          <CheckCircle className="mr-1 h-3 w-3" />
                        )}
                        {session.status}
                      </Badge>
                      <span className="text-xs text-gray-500">{session.timestamp}</span>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
              <CardDescription>
                Common tasks to help with your taxes
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {quickActions.map((action, index) => (
                  <Button
                    key={index}
                    variant="outline"
                    className="w-full justify-start h-auto p-4"
                    onClick={action.action}
                  >
                    <action.icon className="mr-3 h-5 w-5" />
                    <div className="text-left">
                      <div className="font-medium">{action.title}</div>
                      <div className="text-sm text-gray-500">{action.description}</div>
                    </div>
                  </Button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Tax Year Progress */}
          <Card>
            <CardHeader>
              <CardTitle>Tax Year Progress</CardTitle>
              <CardDescription>
                Your 2024 tax preparation status
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <div className="flex items-center justify-between text-sm">
                    <span>Documents Collected</span>
                    <span>8/12</span>
                  </div>
                  <Progress value={67} className="mt-2" />
                </div>
                <div>
                  <div className="flex items-center justify-between text-sm">
                    <span>Deductions Identified</span>
                    <span>8/10</span>
                  </div>
                  <Progress value={80} className="mt-2" />
                </div>
                <div>
                  <div className="flex items-center justify-between text-sm">
                    <span>Optimization Complete</span>
                    <span>6/8</span>
                  </div>
                  <Progress value={75} className="mt-2" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};