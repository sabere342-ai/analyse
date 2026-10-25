import {
  cp,
  lstat,
  mkdir,
  mkdtemp,
  readdir,
  readFile,
  writeFile,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

// Stage only compiled public assets. Never deploy the repository or its store data.
const input = process.argv[2];
if (!input) {
  const root = fileURLToPath(new URL("../", import.meta.url));
  const directory = await mkdtemp(join(tmpdir(), "madrid-vercel-full-"));
  async function copyFile(relative) {
    const source = join(root, relative);
    if (
      !(await lstat(source)).isFile() ||
      (await lstat(source)).isSymbolicLink()
    )
      throw new Error(
        "Only regular source files are allowed in the deployment.",
      );
    const target = join(directory, relative);
    await mkdir(join(target, ".."), { recursive: true });
    await cp(source, target);
  }
  async function copyTree(relative, allow) {
    const source = join(root, relative);
    for (const name of await readdir(source)) {
      const path = join(source, name);
      const stat = await lstat(path);
      if (stat.isSymbolicLink())
        throw new Error("Symlinks are not allowed in deployment sources.");
      if (stat.isDirectory()) {
        if (
          ![
            "__pycache__",
            "node_modules",
            "dist",
            ".cache",
            ".vercel",
          ].includes(name)
        )
          await copyTree(join(relative, name), allow);
      } else if (stat.isFile() && allow(name))
        await copyFile(join(relative, name));
    }
  }
  for (const relative of [
    "pyproject.toml",
    "uv.lock",
    "alembic.ini",
    ".dockerignore",
    "frontend/package.json",
    "frontend/package-lock.json",
    "frontend/index.html",
    "frontend/tsconfig.json",
    "frontend/vite.config.ts",
  ])
    await copyFile(relative);
  await copyTree(
    "madrid",
    (name) => name.endsWith(".py") || name === "font-license.txt",
  );
  await copyTree("migrations", (name) => name.endsWith(".py"));
  await copyTree("frontend/src", () => true);
  await copyTree("frontend/public", () => true);
  const docker = (await readFile(join(root, "Dockerfile"), "utf8"))
    .replace(
      "MADRID_DATA_DIR=/data",
      "MADRID_DATA_DIR=/tmp/madrid-runtime MADRID_REQUIRE_CLOUD_DATABASE=1",
    )
    .replace("XDG_CACHE_HOME=/app/.cache", "XDG_CACHE_HOME=/tmp/madrid-cache");
  await writeFile(join(directory, "Dockerfile.vercel"), docker);
  await writeFile(
    join(directory, ".vercelignore"),
    ".vercel/\n.env*\n**/__pycache__/\n**/node_modules/\n**/dist/\n",
  );
  await writeFile(
    join(directory, "vercel.json"),
    JSON.stringify(
      {
        services: {
          app: {
            root: ".",
            runtime: "container",
            entrypoint: "Dockerfile.vercel",
          },
        },
        rewrites: [{ source: "/(.*)", destination: { service: "app" } }],
      },
      null,
      2,
    ),
  );
  console.log(directory);
  process.exit(0);
}
const backend = new URL(input);
if (
  backend.protocol !== "https:" ||
  backend.username ||
  backend.password ||
  backend.pathname !== "/" ||
  backend.search ||
  backend.hash ||
  !backend.hostname.includes(".") ||
  /^(localhost|127\.|0\.|10\.|192\.168\.|169\.254\.)/.test(backend.hostname) ||
  /\.vercel\.app$/.test(backend.hostname)
)
  throw new Error(
    "Use the persistent backend's public HTTPS origin, without credentials, path or query.",
  );
const source = fileURLToPath(new URL("./dist/", import.meta.url));
async function inspect(directory) {
  for (const name of await readdir(directory)) {
    const path = join(directory, name);
    const stat = await lstat(path);
    if (stat.isSymbolicLink())
      throw new Error("Symlinks are not permitted in deployment assets.");
    if (stat.isDirectory()) await inspect(path);
    else if (!stat.isFile())
      throw new Error("Deployment assets must be regular files.");
  }
}
await inspect(source);
const directory = await mkdtemp(join(tmpdir(), "madrid-vercel-"));
await mkdir(join(directory, "public"));
await cp(source, join(directory, "public"), { recursive: true });
await writeFile(
  join(directory, "vercel.json"),
  JSON.stringify(
    {
      version: 2,
      framework: null,
      outputDirectory: "public",
      headers: [
        {
          source: "/api/:path*",
          headers: [{ key: "Cache-Control", value: "no-store" }],
        },
        {
          source: "/sw.js",
          headers: [{ key: "Cache-Control", value: "no-cache" }],
        },
        {
          source: "/:path*",
          headers: [
            { key: "X-Content-Type-Options", value: "nosniff" },
            { key: "X-Frame-Options", value: "DENY" },
            { key: "Referrer-Policy", value: "no-referrer" },
            {
              key: "Content-Security-Policy",
              value:
                "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'",
            },
          ],
        },
      ],
      rewrites: [
        { source: "/api/:path*", destination: backend.origin + "/api/:path*" },
        { source: "/:path*", destination: "/index.html" },
      ],
    },
    null,
    2,
  ),
);
console.log(directory);
