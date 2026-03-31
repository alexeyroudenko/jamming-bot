'use strict';

var obsidian = require('obsidian');
var child_process = require('child_process');
var path = require('path');

function _interopNamespace(e) {
    if (e && e.__esModule) return e;
    var n = Object.create(null);
    if (e) {
        Object.keys(e).forEach(function (k) {
            if (k !== 'default') {
                var d = Object.getOwnPropertyDescriptor(e, k);
                Object.defineProperty(n, k, d.get ? d : {
                    enumerable: true,
                    get: function () { return e[k]; }
                });
            }
        });
    }
    n["default"] = e;
    return Object.freeze(n);
}

var path__namespace = /*#__PURE__*/_interopNamespace(path);

/******************************************************************************
Copyright (c) Microsoft Corporation.

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
PERFORMANCE OF THIS SOFTWARE.
***************************************************************************** */

function __awaiter(thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
}

class VSCodeProjectPlugin extends obsidian.Plugin {
    onload() {
        return __awaiter(this, void 0, void 0, function* () {
            this.addRibbonIcon('folder', 'Open in Cursor', () => {
                new FileSelectionModal(this.app, this).open();
            });
        });
    }
    openInVSCode(paths) {
        return __awaiter(this, void 0, void 0, function* () {
            const vscodeCommand = 'Cursor'; // Cursor 
            // Get vault path using FileSystemAdapter
            const adapter = this.app.vault.adapter;
            const vaultPath = adapter instanceof obsidian.FileSystemAdapter ? adapter.getBasePath() : '';
            if (!vaultPath) {
                new obsidian.Notice('Unable to get vault path');
                return;
            }
            const convertPath = (p) => path__namespace.join(vaultPath, p);
            const directories = paths.filter(p => this.app.vault.getAbstractFileByPath(p) instanceof obsidian.TFolder);
            const files = paths.filter(p => this.app.vault.getAbstractFileByPath(p) instanceof obsidian.TFile);
            if (directories.length > 0) {
                const fullPath = convertPath(directories[0]);
                const command = `${vscodeCommand} --new-window "${fullPath}"`;
                child_process.exec(command, (error, stdout, stderr) => {
                    if (error) {
                        new obsidian.Notice('Failed to open in Cursor');
                        return;
                    }
                    if (stderr) {
                        console.error(`stderr: ${stderr}`);
                    }
                    if (stdout) {
                        console.log(`stdout: ${stdout}`);
                    }
                    new obsidian.Notice('Directory opened in Cursor');
                });
            }
            else if (files.length > 0) {
                // If no directories are selected but files exist, open all selected files
                const fullPaths = files.map(convertPath);
                const command = `${vscodeCommand} --new-window ${fullPaths.map(p => `"${p}"`).join(' ')}`;
                console.log('Opening files:', fullPaths);
                console.log('Executing command:', command);
                child_process.exec(command, (error, stdout, stderr) => {
                    if (error) {
                        new obsidian.Notice('Failed to open in Cursor');
                        return;
                    }
                    new obsidian.Notice('Files opened in Cursor');
                });
            }
            else {
                new obsidian.Notice('No files or directories selected');
            }
        });
    }
}
class FileSelectionModal extends obsidian.Modal {
    constructor(app, plugin) {
        super(app);
        this.selectedPaths = new Set();
        this.plugin = plugin;
    }
    onOpen() {
        const { contentEl } = this;
        contentEl.empty();
        contentEl.createEl('h2', { text: 'Select Files and Directories' });
        this.renderFileList(contentEl);
        new obsidian.Setting(contentEl)
            .addButton(button => button
            .setButtonText('Open in Cursor')
            .onClick(() => {
            this.plugin.openInVSCode(Array.from(this.selectedPaths));
            this.close();
        }));
    }
    renderFileList(container) {
        const files = this.app.vault.getFiles();
        const fileTree = {};
        files.forEach(file => {
            var _a;
            const folderPath = ((_a = file.parent) === null || _a === void 0 ? void 0 : _a.path) || '';
            if (!fileTree[folderPath]) {
                fileTree[folderPath] = [];
            }
            fileTree[folderPath].push(file);
        });
        Object.keys(fileTree).sort().forEach(folderPath => {
            const folderDiv = container.createEl('div', {
                cls: 'file-tree-folder',
                attr: { style: 'margin-left: 20px;' }
            });
            const folderCheckbox = folderDiv.createEl('input', { type: 'checkbox' });
            folderCheckbox.addEventListener('change', () => {
                if (folderCheckbox.checked) {
                    // When folder is selected, add folder path instead of file paths
                    this.selectedPaths.add(folderPath);
                }
                else {
                    this.selectedPaths.delete(folderPath);
                }
                // Update all child file checkbox states
                const childCheckboxes = folderDiv.querySelectorAll('input[type="checkbox"]');
                childCheckboxes.forEach((cb) => {
                    cb.checked = folderCheckbox.checked;
                    cb.dispatchEvent(new Event('change'));
                });
            });
            folderDiv.createEl('span', { text: folderPath || 'Root', cls: 'file-tree-folder-name' });
            fileTree[folderPath].forEach(file => {
                const fileDiv = folderDiv.createEl('div', {
                    cls: 'file-tree-item',
                    attr: { style: 'margin-left: 20px;' }
                });
                const checkbox = fileDiv.createEl('input', { type: 'checkbox' });
                checkbox.addEventListener('change', () => {
                    const path = this.getFullPath(file);
                    if (checkbox.checked) {
                        this.selectedPaths.add(path);
                    }
                    else {
                        this.selectedPaths.delete(path);
                    }
                });
                fileDiv.createSpan({ text: file.name });
            });
        });
    }
    getFullPath(file) {
        return file.path;
    }
    onClose() {
        const { contentEl } = this;
        contentEl.empty();
    }
}

module.exports = VSCodeProjectPlugin;


/* nosourcemap */