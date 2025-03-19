#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import readline from "node:readline";
import chalk from "chalk";
import clipboardy from "clipboardy";
import { glob } from "glob";
// We only want files in subdirectories of the current working directory.
function findFilesMatching(part) {
    // Glob pattern: "**/*" means any file in any child directory.
    // We ignore node_modules and possibly other hidden folders if you like.
    // Then filter by `part` substring matching.
    const allFiles = glob.sync("**/*", {
        cwd: process.cwd(),
        nodir: true,
        ignore: ["node_modules/**"],
    });
    if (!part)
        return [];
    const lowerPart = part.toLowerCase();
    return allFiles.filter((file) => file.toLowerCase().includes(lowerPart));
}
// Reads entire file content as a string
function readFileContent(filePath) {
    return fs.readFileSync(path.resolve(process.cwd(), filePath), "utf8");
}
// Helper to re-print the prompt line plus suggestions
function reRenderPrompt(rl, input, suggestions, selectedIndex) {
    // We'll do a rough "erase" by going up lines and clearing them
    const linesToMoveUp = suggestions.length + 1;
    for (let i = 0; i < linesToMoveUp; i++) {
        readline.cursorTo(process.stdout, 0);
        readline.moveCursor(process.stdout, 0, -1);
        readline.clearLine(process.stdout, 1);
    }
    // Re-print the welcome label
    process.stdout.write(chalk.blue.bold("Welcome to Prompt!") + "\n");
    // Re-print the prompt input
    process.stdout.write(`> ${input}`);
    // Print suggestions (if any)
    suggestions.forEach((s, i) => {
        const prefix = i === selectedIndex ? chalk.bgWhite.black("> ") : "  ";
        process.stdout.write("\n" + prefix + s);
    });
}
// Start the program
async function main() {
    console.log(chalk.blue.bold("Welcome to Prompt!"));
    // We'll open a readline interface in "raw" mode
    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout,
        terminal: true,
    });
    readline.emitKeypressEvents(process.stdin, rl);
    if (process.stdin.isTTY) {
        process.stdin.setRawMode(true);
    }
    let inputLine = "";
    let suggestions = [];
    let selectedIndex = 0;
    process.stdin.on("keypress", (str, key) => {
        if (key.name === "return") {
            // User pressed Enter
            process.stdout.write("\n");
            rl.close();
            // See if there's a recognized "@filename" in input
            const match = inputLine.match(/@(.*?)(\s|$)/);
            let chosenFile;
            if (match) {
                const afterAt = match[1]; // ex. "app/someFile/route.tsx"
                // If suggestions included it, let's consider it chosen
                if (suggestions.includes(afterAt)) {
                    chosenFile = afterAt;
                }
            }
            let fileContents = "";
            if (chosenFile) {
                fileContents = readFileContent(chosenFile);
            }
            // Build the snippet
            const snippetLines = [];
            snippetLines.push("---");
            if (chosenFile) {
                snippetLines.push(`\`\`\`${chosenFile}`);
                snippetLines.push(fileContents);
                snippetLines.push("```");
            }
            snippetLines.push(inputLine);
            snippetLines.push("---");
            const finalSnippet = snippetLines.join("\n");
            // Copy to clipboard
            clipboardy.writeSync(finalSnippet);
            console.log(chalk.green("\nYour prompt snippet (copied to clipboard):"));
            console.log(finalSnippet);
            process.exit(0);
        }
        else if (key.name === "tab") {
            // Cycle suggestions
            if (suggestions.length > 0) {
                selectedIndex = (selectedIndex + 1) % suggestions.length;
                const atPos = inputLine.lastIndexOf("@");
                if (atPos >= 0) {
                    const beforeAt = inputLine.slice(0, atPos + 1); // keep '@'
                    const selectedFile = suggestions[selectedIndex];
                    inputLine = beforeAt + selectedFile;
                }
                reRenderPrompt(rl, inputLine, suggestions, selectedIndex);
            }
        }
        else if (key.name === "escape" || (key.ctrl && key.name === "c")) {
            process.stdout.write("\n");
            rl.close();
            process.exit(0);
        }
        else if (key.name === "backspace") {
            // remove last char
            inputLine = inputLine.slice(0, -1);
            suggestions = [];
            selectedIndex = 0;
            const atMatch = inputLine.match(/@([^ ]*)$/);
            if (atMatch) {
                suggestions = findFilesMatching(atMatch[1]);
            }
            reRenderPrompt(rl, inputLine, suggestions, selectedIndex);
        }
        else if (key.sequence) {
            // A normal typed character
            inputLine += key.sequence;
            suggestions = [];
            selectedIndex = 0;
            const atMatch = inputLine.match(/@([^ ]*)$/);
            if (atMatch) {
                const partial = atMatch[1] || "";
                suggestions = findFilesMatching(partial);
            }
            reRenderPrompt(rl, inputLine, suggestions, selectedIndex);
        }
    });
    process.stdout.write("> ");
}
main().catch((err) => {
    console.error("Error:", err);
    process.exit(1);
});
