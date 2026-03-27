interface OnboardingProgressProps {
  currentStep: number;
  totalSteps: number;
}

export function OnboardingProgress({
  currentStep,
  totalSteps,
}: OnboardingProgressProps) {
  return (
    <div className="flex gap-2">
      {Array.from({ length: totalSteps }, (_, i) => {
        const step = i + 1;
        let cls = "h-1.5 flex-1 rounded-full transition-colors duration-300 ";
        if (step < currentStep) cls += "bg-primary";
        else if (step === currentStep) cls += "bg-primary/60";
        else cls += "bg-muted";
        return <div key={i} className={cls} />;
      })}
    </div>
  );
}
