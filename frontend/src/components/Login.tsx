import { Mail, Calendar, Folder } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "../api";

export function Login() {
  return (
    <div className="grid h-full grid-cols-1 lg:grid-cols-2">
      {/* form column */}
      <div className="flex items-center justify-center px-6 py-10">
        <div className="flex w-full max-w-[340px] flex-col">
          <div className="mb-10 flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-foreground text-background">
              <span className="text-base font-semibold">C</span>
            </div>
            <span className="text-lg font-semibold tracking-tight">Conductor</span>
          </div>

          <h1 className="text-2xl font-semibold tracking-tight">Sign in</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Orchestrate Gmail, Calendar &amp; Drive with natural language.
          </p>

          <Button
            asChild
            variant="outline"
            size="lg"
            className="mt-8 w-full rounded-full"
          >
            <a href={api.loginUrl}>
              <GoogleMark />
              Continue with Google
            </a>
          </Button>

          <p className="mt-6 text-xs leading-relaxed text-muted-foreground">
            Grants read &amp; draft access to your Workspace. Every send, create, delete, or share
            always requires your explicit confirmation.
          </p>
        </div>
      </div>

      {/* decorative panel */}
      <div className="relative hidden overflow-hidden bg-foreground text-background lg:flex">
        <div
          className="absolute inset-0 opacity-[0.06]"
          style={{
            backgroundImage:
              "radial-gradient(currentColor 1px, transparent 1px)",
            backgroundSize: "22px 22px",
          }}
        />
        <div className="relative z-10 flex flex-col justify-center px-14">
          <div className="text-4xl font-semibold leading-tight tracking-tight">
            One prompt,
            <br />
            your whole Workspace.
          </div>
          <p className="mt-4 max-w-sm text-sm text-background/60">
            Conductor classifies intent, plans a multi-service execution graph, and runs Gmail,
            Calendar &amp; Drive in parallel — then answers in plain language.
          </p>

          <div className="mt-10 flex flex-col gap-3">
            {[
              { icon: Mail, label: "Gmail", sample: "Find emails from LinkedIn about jobs" },
              { icon: Calendar, label: "Calendar", sample: "What's on my calendar next week?" },
              { icon: Folder, label: "Drive", sample: "Show me PDFs from this year" },
            ].map(({ icon: Icon, label, sample }) => (
              <div
                key={label}
                className="flex items-center gap-3 rounded-2xl border border-background/15 bg-background/5 px-4 py-3"
              >
                <Icon className="size-4 shrink-0 text-background/70" />
                <div className="min-w-0">
                  <div className="text-[11px] uppercase tracking-wide text-background/40">{label}</div>
                  <div className="truncate text-sm text-background/80">{sample}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

/** Monochrome Google mark (single-color, fits the black & white theme). */
function GoogleMark() {
  return (
    <svg viewBox="0 0 24 24" className="size-4" fill="currentColor" aria-hidden>
      <path d="M12.24 10.4v3.36h4.68c-.2 1.2-1.42 3.52-4.68 3.52-2.82 0-5.12-2.33-5.12-5.2s2.3-5.2 5.12-5.2c1.6 0 2.68.68 3.3 1.27l2.25-2.17C16.4 4.2 14.53 3.4 12.24 3.4 7.9 3.4 4.4 6.9 4.4 12s3.5 8.6 7.84 8.6c4.53 0 7.53-3.18 7.53-7.67 0-.52-.06-.9-.13-1.3l-7.4.02z" />
    </svg>
  );
}
