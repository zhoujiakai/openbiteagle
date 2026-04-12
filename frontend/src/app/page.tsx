export default function HomePage() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-background">
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-bold text-foreground">Biteagle</h1>
        <p className="text-muted-foreground">Welcome to Biteagle Application</p>
        <p className="text-sm text-muted-foreground">
          Frontend: Next.js + shadcn/ui
        </p>
      </div>
    </main>
  );
}
