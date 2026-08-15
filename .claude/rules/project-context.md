<!-- discovery-metadata: cs=0 xaml=7 deps=1 -->
# UiPath project context

- Root: `UiPath/DocChronoUiPathExamples`
- Type: modern XAML Process
- Target framework: `Windows`
- Expression language: `VisualBasic`
- Entry point: `UiPath/DocChronoUiPathExamples/Main.xaml`
- Dependency: `UiPath.System.Activities [26.6.1]`
- Inventory: 0 coded workflows, 7 XAML workflows, 1 UiPath dependency

Before changing XAML, inspect `UiPath/DocChronoUiPathExamples/project.json`, list Workflow Analyzer rules, and use the restored activity docs under `UiPath/DocChronoUiPathExamples/.local/docs/packages/`. Validate each changed XAML file, then run a project-level build. The Python boundary is `UiPath/DocChronoUiPathExamples/Framework/RunDocChronoBridge.xaml`; keep document payloads in versioned request/response files instead of workflow arguments or logs. The nested project root is also a packaging boundary: do not move Python environments, source documents, generated responses, or case snapshots into it.
