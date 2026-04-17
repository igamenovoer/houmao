export interface TreeNode {
  name: string;
  path: string;
  kind: "file" | "dir";
  children?: TreeNode[];
}

export function renderTree(
  container: HTMLElement,
  root: TreeNode,
  onSelect: (path: string) => void,
): void {
  container.innerHTML = "";
  const ul = document.createElement("ul");
  renderNode(ul, root, onSelect, true);
  container.appendChild(ul);
}

function renderNode(
  parent: HTMLElement,
  node: TreeNode,
  onSelect: (path: string) => void,
  isRoot: boolean,
): void {
  if (node.kind === "dir") {
    if (!isRoot) {
      const li = document.createElement("li");
      li.className = "tree-dir";
      li.textContent = node.name;
      parent.appendChild(li);
    }
    const ul = document.createElement("ul");
    for (const child of node.children ?? []) {
      renderNode(ul, child, onSelect, false);
    }
    parent.appendChild(ul);
  } else {
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.href = `/?page=${encodeURIComponent(node.path)}`;
    a.textContent = node.name;
    a.setAttribute("data-path", node.path);
    a.addEventListener("click", (e) => {
      e.preventDefault();
      onSelect(node.path);
    });
    li.appendChild(a);
    parent.appendChild(li);
  }
}
