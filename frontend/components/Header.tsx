"use client";

import * as React from "react";
import { Switch } from "./ui/switch";
import { Label } from "./ui/label";
import { Button } from "./ui/button";
import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { signOut } from "aws-amplify/auth";
import { LogOut } from "lucide-react";

function ChecklistToggle() {
  const [checklistType, setChecklistType] = useState<"design" | "construction">("design");
  const [mounted, setMounted] = useState(false);
  
  React.useEffect(() => {
    const stored = sessionStorage.getItem('checklist-type') as "design" | "construction";
    if (stored) {
      setChecklistType(stored);
    }
    setMounted(true);
  }, []);

  const handleToggle = (checked: boolean) => {
    const newType = checked ? "construction" : "design";
    setChecklistType(newType);
    sessionStorage.setItem('checklist-type', newType);
    window.dispatchEvent(new CustomEvent('checklistTypeChange', { detail: newType }));
  };

  if (!mounted) {
    return (
      <div className="flex items-center gap-2">
        <Label className="text-xs text-secondary-foreground">Design</Label>
        <Switch disabled />
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <Label className="text-xs text-secondary-foreground">Design</Label>
      <Switch
        checked={checklistType === "construction"}
        onCheckedChange={handleToggle}
        className="data-[state=checked]:bg-green-500"
      />
      <Label className="text-xs text-secondary-foreground">Construction</Label>
    </div>
  );
}

export default function Header() {
  const router = useRouter();

  const handleLogout = async () => {
    try {
      await signOut();
      router.push("/login");
    } catch (error) {
      console.error("Logout error:", error);
    }
  };

  return (
    <nav className="bg-secondary w-full p-3 flex justify-between items-center">
      <div className="flex items-center gap-8">
        <Link href="/" className="font-bold text-md flex flex-row gap-2 items-center text-secondary-foreground">
          <Image src="/logo.png" alt="dxhub logo" width={35} height={35} />
          AI-Powered Project Management
        </Link>
        <div className="flex items-center gap-6">
          <Link href="/" className="text-sm hover:underline hover:text-accent transition-colors text-secondary-foreground">
            Dashboard
          </Link>
          <Link href="/lessons-learned" className="text-sm hover:underline hover:text-accent transition-colors text-secondary-foreground">
            Lessons Learned
          </Link>
          <Link href="/global-checklist" className="text-sm hover:underline hover:text-accent transition-colors text-secondary-foreground">
            Global Checklist
          </Link>
          <Link href="/upload" className="text-sm hover:underline hover:text-accent transition-colors text-secondary-foreground">
            Upload
          </Link>
          <ChecklistToggle />
        </div>
      </div>
      <Button
        variant="ghost"
        size="sm"
        onClick={handleLogout}
        className="text-red-600 hover:text-red-700"
      >
        <LogOut className="h-4 w-4 mr-2" />
        Logout
      </Button>
    </nav>
  );
}
