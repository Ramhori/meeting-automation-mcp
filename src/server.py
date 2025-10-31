# Smithery configuration file: https://smithery.ai/docs/config#smitheryyaml

startCommand:
  type: stdio
  configSchema:
    type: object
    properties: {}
  commandFunction: |-
    (config) => ({
      command: 'python',
      args: ['src/server.py']
    })
  exampleConfig: {}
```

### 최종 구조:
```
meeting-automation-mcp/
├── src/
│   └── server.py       ← 이동!
├── requirements.txt
├── smithery.yaml       ← args: ['src/server.py']
├── README.md
└── LICENSE
