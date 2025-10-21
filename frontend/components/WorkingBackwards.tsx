"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Users, Target, AlertTriangle, Lightbulb, HelpCircle, CheckCircle } from "lucide-react";

interface WorkingBackwardsData {
  workingBackwards: {
    customerContext: string;
    explicitNeeds: string[];
    implicitNeeds: string[];
    prioritySignals: string[];
    requirementsClassification: {
      mustHaveRequirements: string[];
      niceToHaveFeatures: string[];
      futureConsiderations: string[];
      outOfScopeItems: string[];
    };
    keyPainPoints: string[];
    opportunities: string[];
    followUpQuestions: string[];
  };
}

interface WorkingBackwardsProps {
  workingBackwardsData: WorkingBackwardsData | null;
}

export default function WorkingBackwards({ workingBackwardsData }: WorkingBackwardsProps) {
  if (!workingBackwardsData?.workingBackwards) {
    return (
      <div className="space-y-6">
        <Card>
          <CardContent className="p-6">
            <p className="text-muted-foreground">No working backwards analysis available</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const wb = workingBackwardsData.workingBackwards;

  return (
    <div className="space-y-6">
      {/* Customer Context */}
      {wb.customerContext && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              Customer Context
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-relaxed">{wb.customerContext}</p>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Explicit Needs */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5" />
              Explicit Needs ({wb.explicitNeeds.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {wb.explicitNeeds.length > 0 ? (
              <ul className="space-y-2">
                {wb.explicitNeeds.map((need, index) => (
                  <li key={index} className="flex items-start gap-2">
                    <span className="text-primary font-medium text-sm mt-0.5">•</span>
                    <span className="text-sm leading-relaxed">{need}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-muted-foreground text-sm">No explicit needs identified</p>
            )}
          </CardContent>
        </Card>

        {/* Implicit Needs */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="h-5 w-5" />
              Implicit Needs ({wb.implicitNeeds.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {wb.implicitNeeds.length > 0 ? (
              <ul className="space-y-2">
                {wb.implicitNeeds.map((need, index) => (
                  <li key={index} className="flex items-start gap-2">
                    <span className="text-primary font-medium text-sm mt-0.5">•</span>
                    <span className="text-sm leading-relaxed">{need}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-muted-foreground text-sm">No implicit needs identified</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Requirements Classification */}
      <Card>
        <CardHeader>
          <CardTitle>Requirements Classification</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h4 className="font-medium text-sm mb-2 text-red-600">Must-Have Requirements</h4>
              {wb.requirementsClassification.mustHaveRequirements.length > 0 ? (
                <ul className="space-y-1">
                  {wb.requirementsClassification.mustHaveRequirements.map((req, index) => (
                    <li key={index} className="text-sm">• {req}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-muted-foreground text-sm">None identified</p>
              )}
            </div>
            <div>
              <h4 className="font-medium text-sm mb-2 text-blue-600">Nice-to-Have Features</h4>
              {wb.requirementsClassification.niceToHaveFeatures.length > 0 ? (
                <ul className="space-y-1">
                  {wb.requirementsClassification.niceToHaveFeatures.map((feature, index) => (
                    <li key={index} className="text-sm">• {feature}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-muted-foreground text-sm">None identified</p>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Key Pain Points */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              Key Pain Points ({wb.keyPainPoints.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {wb.keyPainPoints.length > 0 ? (
              <ul className="space-y-2">
                {wb.keyPainPoints.map((pain, index) => (
                  <li key={index} className="flex items-start gap-2">
                    <span className="text-red-500 font-medium text-sm mt-0.5">•</span>
                    <span className="text-sm leading-relaxed">{pain}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-muted-foreground text-sm">No pain points identified</p>
            )}
          </CardContent>
        </Card>

        {/* Opportunities */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Lightbulb className="h-5 w-5" />
              Opportunities ({wb.opportunities.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {wb.opportunities.length > 0 ? (
              <ul className="space-y-2">
                {wb.opportunities.map((opportunity, index) => (
                  <li key={index} className="flex items-start gap-2">
                    <span className="text-green-500 font-medium text-sm mt-0.5">•</span>
                    <span className="text-sm leading-relaxed">{opportunity}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-muted-foreground text-sm">No opportunities identified</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Follow-up Questions */}
      {wb.followUpQuestions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <HelpCircle className="h-5 w-5" />
              Follow-up Questions ({wb.followUpQuestions.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {wb.followUpQuestions.map((question, index) => (
                <li key={index} className="flex items-start gap-2">
                  <span className="text-blue-500 font-medium text-sm mt-0.5">?</span>
                  <span className="text-sm leading-relaxed">{question}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
