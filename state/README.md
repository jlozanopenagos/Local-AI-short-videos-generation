# State Directory

This directory stores real-time JSON execution states for each script as it moves through the pipeline stages:
1. `_A_video_scripts`: Script text generation & YouTube metadata
2. `_B_voice_generation`: Speech synthesis audio paths & timing
3. `_C_image_generation`: Scene illustrations
4. `_D_music_generation`: Background jam assignment
5. `_F_thumbnail_image_generation`: YouTube thumbnail
6. `_G_video_assembly`: Final assembled MP4 video

## Structure
```
state/
├── english/
│   ├── expression/
│   ├── game/
│   ├── roleplay/
│   └── fun_facts/
├── french/
│   ├── expression/
│   ├── game/
│   ├── roleplay/
│   └── fun_facts/
├── spanish/
│   ├── expression/
│   ├── game/
│   ├── roleplay/
│   └── fun_facts/
└── italian/
    ├── expression/
    ├── game/
    ├── roleplay/
    └── fun_facts/
```

Individual script state files (`script_<ID>.json`) and `pipeline_status.csv` are generated dynamically by pipeline runs and are ignored by git to keep commits clean.
A sample reference schema is provided in [`script_state.sample.json`](script_state.sample.json).
