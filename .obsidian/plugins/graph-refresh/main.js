const { Plugin } = require("obsidian");

// Node Factor only sizes nodes on startup and on active-leaf-change, and gives up
// if the graph hasn't loaded its nodes yet. This plugin calls Node Factor again
// whenever the graph receives new data, and once its nodes first appear.

const POLL_MS = 300;
const POLL_LIMIT = 40; // ~12 seconds

module.exports = class GraphRedrawNudge extends Plugin {
  onload() {
    this.patched = new WeakSet();

    this.app.workspace.onLayoutReady(() => this.scan());
    this.registerEvent(this.app.workspace.on("layout-change", () => this.scan()));
    this.registerEvent(this.app.workspace.on("active-leaf-change", () => this.scan()));

    this.addCommand({
      id: "reapply-node-factor",
      name: "Reapply Node Factor sizes",
      callback: () => this.apply(),
    });
  }

  getNodeFactor() {
    const plugins = this.app.plugins?.plugins ?? {};
    return (
      plugins["node-factor"] ??
      Object.values(plugins).find(
        (p) => typeof p?.updateGraph === "function" && p.sizeCache instanceof Map
      )
    );
  }

  apply() {
    const nf = this.getNodeFactor();
    if (nf) nf.updateGraph();
    else console.warn("[graph-redraw-nudge] Node Factor not found or not enabled.");
  }

  scan() {
    for (const leaf of this.app.workspace.getLeavesOfType("graph")) {
      const renderer = leaf.view?.renderer;
      if (!renderer || this.patched.has(renderer)) continue; // deferred tab: caught on a later event
      this.patched.add(renderer);

      // 1) Re-apply sizes every time Obsidian pushes new graph data (this resets weights).
      if (typeof renderer.setData === "function") {
        const original = renderer.setData;
        const plugin = this;
        const wrapper = function (...args) {
          const result = original.apply(this, args);
          plugin.apply();
          return result;
        };
        renderer.setData = wrapper;
        this.register(() => {
          if (renderer.setData === wrapper) renderer.setData = original;
        });
      }

      // 2) Fallback: wait until nodes exist, then apply once.
      this.waitForNodes(renderer, 0);
    }
  }

  waitForNodes(renderer, attempt) {
    if (renderer.nodes?.length > 0) {
      this.apply();
      return;
    }
    if (attempt >= POLL_LIMIT) return;
    const id = window.setTimeout(() => this.waitForNodes(renderer, attempt + 1), POLL_MS);
    this.register(() => window.clearTimeout(id));
  }
};
