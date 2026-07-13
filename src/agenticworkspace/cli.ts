#!/usr/bin/env node
import { Command } from "commander";
import { runInitCommand } from "./commands/init.js";
import { runStatusCommand } from "./commands/status.js";
import { runHandoffNewCommand } from "./commands/handoff.js";
import { runScanCommand } from "./commands/scan.js";
import { runAdapterInstallCommand } from "./commands/adapter.js";
import { AGENTICWORKSPACE_VERSION } from "./scaffold/init-engine.js";

interface CommandOutcome {
  exitCode: number;
  json: Record<string, unknown>;
  humanLines: string[];
}

function emit(outcome: CommandOutcome, jsonMode: boolean): void {
  if (jsonMode) {
    console.log(JSON.stringify(outcome.json, null, 2));
  } else {
    for (const line of outcome.humanLines) {
      console.log(line);
    }
  }
  process.exitCode = outcome.exitCode;
}

const program = new Command();

program
  .name("agenticworkspace")
  .description("Convert any repository into an agent-ready workspace: stack detection, progressive context, session handoffs, and a Claude Code adapter.")
  .version(AGENTICWORKSPACE_VERSION);

program
  .command("init")
  .description("Scan the repo and write the .workspace/ scaffold plus the Claude Code adapter")
  .option("-p, --path <path>", "path to the target repo", process.cwd())
  .option("--json", "output structured JSON instead of human-readable text")
  .action(async (opts) => {
    const outcome = await runInitCommand({ path: opts.path, json: Boolean(opts.json) });
    emit(outcome, Boolean(opts.json));
  });

program
  .command("scan")
  .description("Detect stack and existing agent-tooling surface, no writes")
  .option("-p, --path <path>", "path to the target repo", process.cwd())
  .option("--json", "output structured JSON instead of human-readable text")
  .action(async (opts) => {
    const outcome = await runScanCommand({ path: opts.path, json: Boolean(opts.json) });
    emit(outcome, Boolean(opts.json));
  });

program
  .command("status")
  .description("Report workspace health: stack, context budget, handoffs, adapter staleness")
  .option("-p, --path <path>", "path to the target repo", process.cwd())
  .option("--json", "output structured JSON instead of human-readable text")
  .action(async (opts) => {
    const outcome = await runStatusCommand({ path: opts.path, json: Boolean(opts.json) });
    emit(outcome, Boolean(opts.json));
  });

const adapterCommand = program.command("adapter").description("Manage tool adapters");

adapterCommand
  .command("install <name>")
  .description("(Re)install a single adapter's hook wiring (e.g. claude-code)")
  .option("-p, --path <path>", "path to the target repo", process.cwd())
  .option("--json", "output structured JSON instead of human-readable text")
  .action(async (name: string, opts) => {
    const outcome = await runAdapterInstallCommand(name, { path: opts.path, json: Boolean(opts.json) });
    emit(outcome, Boolean(opts.json));
  });

const handoffCommand = program.command("handoff").description("Manage session handoff files");

handoffCommand
  .command("new <message>")
  .description("Write a new timestamped handoff file")
  .option("-p, --path <path>", "path to the target repo", process.cwd())
  .option("--json", "output structured JSON instead of human-readable text")
  .action(async (message: string, opts) => {
    const outcome = await runHandoffNewCommand(message, { path: opts.path, json: Boolean(opts.json) });
    emit(outcome, Boolean(opts.json));
  });

program.parseAsync(process.argv).catch((error: unknown) => {
  const message = error instanceof Error ? error.message : String(error);
  console.error(`agenticworkspace: ${message}`);
  process.exitCode = 1;
});
