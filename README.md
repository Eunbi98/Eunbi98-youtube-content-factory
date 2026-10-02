# YouTube Content Factory

## Data-driven episode

새 에피소드는 Python 파일을 수정하지 않고 아래 경로에
`episode.json`을 추가하여 생성합니다.

```text
projects/episodes/ep014/episode.json
```

기본 형식은 다음 예제 파일을 복사해 사용합니다.

```text
projects/episodes/episode.example.json
```

`scenes[].narration`은 TTS와 자막에 동일하게 사용됩니다.
첫 Scene은 `hook`, 마지막 Scene은 `ending`이어야 합니다.
미디어 `src`를 생략하면 다음 규칙으로 자동 생성됩니다.

```text
ep014/scene_001.jpg
ep014/scene_002.jpg
```

실행:

```powershell
py factory_runner.py --episode ep014 --rebuild-timeline
```

Episode Spec 테스트:

```powershell
py -m unittest discover -s tests -v
```

원격 렌더:

```text
GitHub → Actions → Render episode → Run workflow
```

`episode_id`에 `ep014` 같은 값을 입력하면 GitHub가 Factory를
실행합니다. 성공한 MP4는 해당 Workflow Run의 Artifacts에서
14일 동안 다운로드할 수 있습니다.

기존 EP008~EP013 Python Story Builder는 호환성을 위해 유지됩니다.
같은 에피소드 폴더에 `episode.json`이 있으면 JSON을 우선 사용합니다.

## Legacy Mystery Plugin Integration

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
