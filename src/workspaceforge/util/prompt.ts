import * as readline from "node:readline/promises";

/** Ask a free-form question and return the trimmed answer. */
export async function ask(question: string): Promise<string> {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  try {
    const answer = await rl.question(question);
    return answer.trim();
  } finally {
    rl.close();
  }
}

/** Ask a yes/no question. Defaults to `defaultYes` if the user just presses enter. */
export async function askYesNo(question: string, defaultYes = true): Promise<boolean> {
  const suffix = defaultYes ? "[Y/n]" : "[y/N]";
  const answer = (await ask(`${question} ${suffix} `)).toLowerCase();
  if (answer === "") {
    return defaultYes;
  }
  return answer === "y" || answer === "yes";
}

export type RepairResetAbortChoice = "repair" | "reset" | "abort";

/** Ask the repair / reset / abort question used by partial-state handling. */
export async function askRepairResetAbort(): Promise<RepairResetAbortChoice> {
  const answer = (
    await ask("Choose an option: [r]epair / reset ([w]ipe and start clean) / [a]bort: ")
  ).toLowerCase();
  if (answer.startsWith("r") && !answer.startsWith("re")) {
    return "repair";
  }
  if (answer === "repair") {
    return "repair";
  }
  if (answer.startsWith("w") || answer === "reset") {
    return "reset";
  }
  return "abort";
}

export function isInteractiveTerminal(): boolean {
  return Boolean(process.stdin.isTTY) && Boolean(process.stdout.isTTY);
}
