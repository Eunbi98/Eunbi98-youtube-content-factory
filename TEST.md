# TEST

```powershell
python projects\plugins\mystery\build_evidence.py
python -m compileall projects\plugins\mystery
python projects\plugins\mystery\build_mystery.py
```

예상:

```text
Mystery Plugin End-to-End 완료
Episode: ep009
주제: 버뮤다 삼각지대
Scene 수: 5
전체 길이: XX.XXX초
출력 경로: projects/episodes/ep009/timeline.json
```

검증:

```powershell
Get-Content projects\episodes\ep009\timeline.json
```
