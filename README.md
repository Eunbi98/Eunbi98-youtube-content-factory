# Release 6 Feature 5 — Mystery Plugin Integration

## 적용 파일

```text
projects/plugins/mystery/mystery_plugin.py
projects/plugins/mystery/build_mystery.py
```

두 파일 모두 기존 파일을 덮어씁니다.

## 실행

Evidence 결과를 먼저 생성합니다.

```powershell
python projects\plugins\mystery\build_evidence.py
python -m compileall projects\plugins\mystery
python projects\plugins\mystery\build_mystery.py
```

다른 주제로 실행:

```powershell
python projects\plugins\mystery\build_mystery.py `
  --episode-id ep010 `
  --topic "사라진 도시" `
  --output "projects/episodes/ep010/timeline.json"
```

## 최종 API

```python
result = MysteryPlugin().build(
    episode_id="ep010",
    topic="사라진 도시",
    evidence_path="projects/plugins/mystery/output/evidence_result.json",
    output_path="projects/episodes/ep010/timeline.json",
)
```

## Release 6 완료 구조

```text
Research Plan
→ Evidence Collector
→ Story Planner
→ Story Optimizer
→ Story Validator
→ Factory Core
→ Timeline JSON
```
