import json
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import PurePosixPath

from app.schemas import (
    PrototypeManifestResponse as PrototypeManifest,
)
from app.schemas import (
    PrototypePlanResponse as PrototypePlan,
)
from app.schemas import (
    PrototypeScreenPlan as PrototypeScreen,
)
from app.schemas import (
    RequirementSpecification,
)

TEMPLATE_ID = "education-placement-preparation"
TEMPLATE_VERSION = "1"
FRAMEWORK = "react-typescript-vite"

APPROVED_DEPENDENCIES = {
    "react": "19.2.8",
    "react-dom": "19.2.8",
    "vite": "8.2.0",
    "typescript": "6.0.2",
    "@vitejs/plugin-react": "6.0.4",
}
APPROVED_SCRIPTS = {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "typecheck": "tsc -b",
}
ALLOWED_FILES = {
    "index.html",
    "package.json",
    "tsconfig.json",
    "vite.config.ts",
    "src/Prototype.tsx",
    "src/main.tsx",
    "src/prototype.json",
    "src/styles.css",
}
REQUIRED_FILES = ALLOWED_FILES
MAX_SOURCE_BYTES = 128 * 1024
UNSAFE_SOURCE_PATTERNS = (
    re.compile(r"\beval\s*\("),
    re.compile(r"\bnew\s+Function\s*\("),
    re.compile(r"\bfetch\s*\("),
    re.compile(r"\bXMLHttpRequest\b"),
    re.compile(r"\bprocess\.env\b"),
    re.compile(r"\bimport\s*\("),
    re.compile(r"\brequire\s*\("),
    re.compile(r"\bdangerouslySetInnerHTML\b"),
    re.compile(r"\bchild_process\b"),
)
ALLOWED_IMPORTS = {
    "react",
    "react-dom/client",
    "vite",
    "@vitejs/plugin-react",
    "./Prototype",
    "./styles.css",
    "./prototype.json",
}
IMPORT_PATTERN = re.compile(
    r"""(?:from\s*|import\s*)['"]([^'"]+)['"]""",
)


class PrototypeValidationError(ValueError):
    pass


class UnsupportedPrototypeCategory(ValueError):
    pass


@dataclass(frozen=True)
class GeneratedPrototype:
    plan: PrototypePlan
    manifest: PrototypeManifest
    files: dict[str, str]


@dataclass(frozen=True)
class SourceFileMetadata:
    path: str
    sha256: str
    size_bytes: int

    def as_dict(self) -> dict[str, str | int]:
        return {"path": self.path, "sha256": self.sha256, "size_bytes": self.size_bytes}


def supports_education_placement(
    category: str,
    title: str,
    problem: str,
    solution: str,
    audience: str,
    features: list[str],
) -> bool:
    if category.strip().casefold() != "education":
        return False
    source = " ".join([title, problem, solution, audience, *features]).casefold()
    return any(
        signal in source
        for signal in (
            "placement",
            "career",
            "job",
            "resume",
            "student",
            "internship",
        )
    )


def _safe_json(value: object) -> str:
    return (
        json.dumps(value, ensure_ascii=True, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


def _prototype_data(
    title: str,
    source_version: int,
    requirements: RequirementSpecification,
) -> dict:
    return {
        "title": title,
        "source_version": source_version,
        "notice": "Generated source only. This has not been built or published.",
        "problem": [fact.model_dump(mode="json") for fact in requirements.problem],
        "target_users": [fact.model_dump(mode="json") for fact in requirements.target_users],
        "features": [
            fact.model_dump(mode="json")
            for fact in requirements.core_features
            if fact.basis == "explicit"
        ],
        "journeys": [
            journey.model_dump(mode="json") for journey in requirements.user_journeys
        ],
        "open_questions": requirements.open_questions,
        "limitations": [
            "Interactions are local prototype-only behavior; no external service is connected.",
            "Generated source has not been executed, built, or security-tested in isolation.",
            "No working preview is available until a restricted build boundary is supplied.",
        ],
    }


def generate_education_placement_prototype(
    *,
    category: str,
    title: str,
    problem: str,
    solution: str,
    audience: str,
    features: list[str],
    source_version: int,
    requirements: RequirementSpecification,
) -> GeneratedPrototype:
    if not supports_education_placement(
        category, title, problem, solution, audience, features
    ):
        raise UnsupportedPrototypeCategory(
            "The only supported builder category is education placement preparation."
        )

    plan = PrototypePlan(
        template_id=TEMPLATE_ID,
        template_version="1.0",
        framework=FRAMEWORK,
        category="education-placement",
        screens=[
            PrototypeScreen(
                key="overview",
                title="Overview",
                components=[
                    {"name": "PrototypeNotice", "purpose": "Show source/build status."},
                    {"name": "IdeaSummary", "purpose": "Present validated source facts."},
                ],
            ),
            PrototypeScreen(
                key="features",
                title="Features",
                components=[
                    {"name": "FeatureSearch", "purpose": "Search explicit core features."},
                ],
            ),
            PrototypeScreen(
                key="journeys",
                title="User journeys",
                components=[
                    {"name": "JourneySteps", "purpose": "Present validated journey steps."},
                ],
            ),
            PrototypeScreen(
                key="questions",
                title="Open questions",
                components=[
                    {"name": "OpenQuestions", "purpose": "Expose unresolved requirements."},
                ],
            ),
        ],
        limitations=[
            "Uses only the approved placement-preparation template and local content.",
            "Does not connect to real jobs, resumes, accounts, or external services.",
            "Source is not a built or published working prototype.",
        ],
    )
    manifest = PrototypeManifest(
        template_id=TEMPLATE_ID,
        template_version="1.0",
        framework=FRAMEWORK,
        dependencies=APPROVED_DEPENDENCIES,
        scripts=APPROVED_SCRIPTS,
        files=sorted(ALLOWED_FILES),
        source_only=True,
        build_boundary="unavailable",
    )
    files = {
        "index.html": """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Veridica generated source</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
""",
        "package.json": _safe_json(
            {
                "name": "veridica-generated-prototype",
                "private": True,
                "version": "0.0.0",
                "type": "module",
                "scripts": APPROVED_SCRIPTS,
                "dependencies": {
                    "react": APPROVED_DEPENDENCIES["react"],
                    "react-dom": APPROVED_DEPENDENCIES["react-dom"],
                },
                "devDependencies": {
                    "@vitejs/plugin-react": APPROVED_DEPENDENCIES["@vitejs/plugin-react"],
                    "typescript": APPROVED_DEPENDENCIES["typescript"],
                    "vite": APPROVED_DEPENDENCIES["vite"],
                },
            }
        ),
        "tsconfig.json": _safe_json(
            {
                "compilerOptions": {
                    "target": "ES2022",
                    "useDefineForClassFields": True,
                    "lib": ["ES2022", "DOM", "DOM.Iterable"],
                    "module": "ESNext",
                    "skipLibCheck": True,
                    "moduleResolution": "Bundler",
                    "allowImportingTsExtensions": True,
                    "verbatimModuleSyntax": True,
                    "moduleDetection": "force",
                    "noEmit": True,
                    "jsx": "react-jsx",
                    "strict": True,
                    "noUnusedLocals": True,
                    "noUnusedParameters": True,
                },
                "include": ["src"],
            }
        ),
        "vite.config.ts": """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({ plugins: [react()] })
""",
        "src/main.tsx": """import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import Prototype from './Prototype'
import './styles.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode><Prototype /></StrictMode>,
)
""",
        "src/Prototype.tsx": """import { useMemo, useState } from 'react'
import prototype from './prototype.json'

const screens = [
  ['overview', 'Overview'],
  ['features', 'Features'],
  ['journeys', 'User journeys'],
  ['questions', 'Open questions'],
] as const

export default function Prototype() {
  const [screen, setScreen] = useState<(typeof screens)[number][0]>('overview')
  const [query, setQuery] = useState('')
  const visibleFeatures = useMemo(
    () => prototype.features.filter((item) =>
      item.text.toLowerCase().includes(query.toLowerCase())),
    [query],
  )
  return <main>
    <header>
      <p>VERIDICA · GENERATED SOURCE</p>
      <h1>{prototype.title}</h1>
      <span>Idea version {prototype.source_version}</span>
    </header>
    <aside role="note">{prototype.notice}</aside>
    <nav aria-label="Prototype screens">
      {screens.map(([key, label]) => <button
        key={key}
        aria-current={screen === key ? 'page' : undefined}
        onClick={() => setScreen(key)}
      >{label}</button>)}
    </nav>
    {screen === 'overview' && <section>
      <h2>Idea summary</h2>
      {prototype.problem.map((fact, index) =>
        <p key={`problem-${index}`}>{fact.text} <small>{fact.basis}</small></p>)}
      {prototype.target_users.map((fact, index) =>
        <p key={`users-${index}`}>For {fact.text} <small>{fact.basis}</small></p>)}
    </section>}
    {screen === 'features' && <section>
      <h2>Supported features</h2>
      <label>Search features
        <input value={query} onChange={(event) => setQuery(event.target.value)} />
      </label>
      {visibleFeatures.length
        ? <ul>{visibleFeatures.map((feature, index) =>
          <li key={`${feature.text}-${index}`}>
            {feature.text} <small>{feature.basis}</small>
          </li>)}</ul>
        : <p>No explicit features found.</p>}
    </section>}
    {screen === 'journeys' && <section>
      <h2>User journeys</h2>
      {prototype.journeys.length
        ? prototype.journeys.map((journey, index) => <article
          key={`${journey.actor.text}-${index}`}
        >
          <h3>{journey.actor.text}</h3>
          <p>{journey.need.text}</p>
          <ol>{journey.steps.map((step) => <li key={step}>{step}</li>)}</ol>
          <p>{journey.outcome.text}</p>
        </article>)
        : <p>No validated journeys supplied.</p>}
    </section>}
    {screen === 'questions' && <section>
      <h2>Open questions</h2>
      {prototype.open_questions.length
        ? <ul>{prototype.open_questions.map((question) =>
          <li key={question}>{question}</li>)}</ul>
        : <p>No open questions supplied.</p>}
    </section>}
    <footer>
      <h2>Limitations</h2>
      <ul>{prototype.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
    </footer>
  </main>
}
""",
        "src/prototype.json": _safe_json(
            _prototype_data(title, source_version, requirements)
        ),
        "src/styles.css": """* { box-sizing: border-box; }
body { margin: 0; background: #f4f7f5; color: #172923; font: 16px/1.5 system-ui, sans-serif; }
main { max-width: 960px; margin: 2rem auto; padding: 1rem; }
header, section, footer, aside {
  background: white;
  border: 1px solid #dbe5df;
  border-radius: 1rem;
  margin: 1rem 0;
  padding: 1.25rem;
}
nav { display: flex; flex-wrap: wrap; gap: .5rem; }
button, input { border: 1px solid #9aaca2; border-radius: .5rem; padding: .65rem .9rem; }
button[aria-current="page"] { background: #174b3b; color: white; }
small { color: #52675d; }
@media (max-width: 600px) {
  main { margin: .5rem auto; }
  nav button { flex: 1 1 42%; }
}
""",
    }
    validate_generated_files(files)
    return GeneratedPrototype(plan=plan, manifest=manifest, files=files)


def validate_generated_files(files: dict[str, str]) -> list[SourceFileMetadata]:
    for filename in files:
        _validate_source_path(filename)
    if set(files) != REQUIRED_FILES:
        missing = sorted(REQUIRED_FILES - set(files))
        extra = sorted(set(files) - REQUIRED_FILES)
        raise PrototypeValidationError(
            f"Generated file set is invalid (missing={missing}, extra={extra})."
        )
    total_bytes = 0
    metadata: list[SourceFileMetadata] = []
    for filename, content in files.items():
        if not isinstance(filename, str) or not isinstance(content, str):
            raise PrototypeValidationError("Generated source file entries must be text.")
        encoded = content.encode("utf-8")
        total_bytes += len(encoded)
        metadata.append(
            SourceFileMetadata(
                path=filename,
                sha256=sha256(encoded).hexdigest(),
                size_bytes=len(encoded),
            )
        )
        if filename.endswith((".ts", ".tsx")) and any(
            pattern.search(content) for pattern in UNSAFE_SOURCE_PATTERNS
        ):
            raise PrototypeValidationError(
                f"Generated source contains a disallowed capability: {filename}."
            )
        if filename.endswith((".ts", ".tsx")) and any(
            module not in ALLOWED_IMPORTS for module in IMPORT_PATTERN.findall(content)
        ):
            raise PrototypeValidationError(
                f"Generated source contains an unapproved import: {filename}."
            )
    if total_bytes > MAX_SOURCE_BYTES:
        raise PrototypeValidationError("Generated source exceeds the size limit.")

    try:
        package = json.loads(files["package.json"])
        dependencies = {
            **package.get("dependencies", {}),
            **package.get("devDependencies", {}),
        }
    except (json.JSONDecodeError, AttributeError, TypeError) as error:
        raise PrototypeValidationError("Generated package manifest is invalid.") from error
    if dependencies != APPROVED_DEPENDENCIES:
        raise PrototypeValidationError("Generated package contains unsupported dependencies.")
    if package.get("scripts") != APPROVED_SCRIPTS:
        raise PrototypeValidationError("Generated package contains unsupported scripts.")
    return sorted(metadata, key=lambda item: item.path)


def _validate_source_path(filename: str) -> None:
    if not isinstance(filename, str) or "\\" in filename or ":" in filename:
        raise PrototypeValidationError("Generated source path is not allowed.")
    parts = filename.split("/")
    path = PurePosixPath(filename)
    if (
        path.is_absolute()
        or any(part in {"", ".", ".."} for part in parts)
        or path.as_posix() != filename
        or filename not in ALLOWED_FILES
    ):
        raise PrototypeValidationError("Generated source path is not allowed.")


def write_source_files(
    storage_dir: str,
    storage_key: str,
    files: dict[str, str],
    metadata: list[SourceFileMetadata],
) -> None:
    from pathlib import Path

    root = Path(storage_dir).resolve()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    build_dir = root / storage_key
    build_dir.mkdir(mode=0o700, exist_ok=False)
    resolved_build_dir = build_dir.resolve(strict=True)
    expected_metadata = {item.path: item for item in metadata}
    try:
        for filename, content in files.items():
            _validate_source_path(filename)
            parts = PurePosixPath(filename).parts
            target = build_dir.joinpath(*parts)
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            resolved_parent = target.parent.resolve(strict=True)
            if not resolved_parent.is_relative_to(resolved_build_dir):
                raise PrototypeValidationError(
                    "Generated source path escaped its storage directory."
                )
            info = expected_metadata[filename]
            encoded = content.encode("utf-8")
            if sha256(encoded).hexdigest() != info.sha256 or len(encoded) != info.size_bytes:
                raise PrototypeValidationError("Generated source changed after validation.")
            with target.open("xb") as output:
                output.write(encoded)
            target.chmod(0o600)
    except (OSError, PrototypeValidationError):
        import shutil

        shutil.rmtree(build_dir, ignore_errors=True)
        raise


def read_source_files(
    storage_dir: str,
    storage_key: str,
    metadata: list[dict],
) -> dict[str, str]:
    from pathlib import Path

    root = Path(storage_dir).resolve()
    build_dir = root / storage_key
    try:
        resolved_build_dir = build_dir.resolve(strict=True)
    except OSError as error:
        raise FileNotFoundError("Generated source artifact is missing.") from error
    if not resolved_build_dir.is_relative_to(root):
        raise PrototypeValidationError("Generated source storage location is invalid.")
    result: dict[str, str] = {}
    for item in metadata:
        filename = item.get("path")
        try:
            _validate_source_path(filename)
        except PrototypeValidationError as error:
            raise PrototypeValidationError("Generated source metadata is invalid.") from error
        target = build_dir.joinpath(*PurePosixPath(filename).parts)
        try:
            if target.is_symlink() or not target.is_file():
                raise FileNotFoundError
            resolved = target.resolve(strict=True)
            if not resolved.is_relative_to(resolved_build_dir):
                raise PrototypeValidationError(
                    "Generated source path escaped its storage directory."
                )
            encoded = resolved.read_bytes()
        except OSError as error:
            raise FileNotFoundError("Generated source artifact is missing.") from error
        if (
            len(encoded) != item.get("size_bytes")
            or sha256(encoded).hexdigest() != item.get("sha256")
        ):
            raise FileNotFoundError("Generated source artifact failed integrity verification.")
        result[filename] = encoded.decode("utf-8")
    if set(result) != REQUIRED_FILES:
        raise FileNotFoundError("Generated source artifact is incomplete.")
    return result
