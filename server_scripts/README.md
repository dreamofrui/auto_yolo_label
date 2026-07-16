# Server Scripts

These standalone scripts run training and prediction without opening the desktop
GUI and without importing the rest of the AutoLabeler project. They are intended
for an offline Ubuntu GPU server or an Ultralytics Docker container after the
Python environment is already prepared.

Run commands from the directory that contains `server_scripts`:

```bash
cd /usr/src/app
```

## Environment Check

The server Python must be able to import Ultralytics runtime dependencies and
should use a CUDA-enabled PyTorch build for GPU work:

```bash
python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NO CUDA')"
python -c "from ultralytics import YOLO; import PIL, cv2, yaml; print('imports ok')"
```

If `torch.cuda.is_available()` prints `False`, `--device gpu` will fail and the
run should use `--device cpu` until the server environment has CUDA PyTorch.

## Train

```bash
python server_scripts/train_yolo.py \
  --data-yaml /data/dataset/data.yaml \
  --base-model /data/models/yolov8n.pt \
  --output-dir /data/runs/train \
  --device gpu \
  --epochs 100 \
  --imgsz 640 \
  --batch -1
```

Useful options:

- `--device auto|cpu|gpu|0|0,1`
- `--batch -1` lets Ultralytics choose the training batch size.
- `--run-name name` fixes the YOLO run folder name under `--output-dir`.
- `--overwrite` allows reusing an existing run name.
- `--cache ram|disk|true|false`
- `--log-file path` writes terminal output to a log file. If omitted, the
  script writes `train_YYYYMMDD_HHMMSS.log` under `--output-dir`.

The script prints the output folder plus `best.pt` and `last.pt` paths when
training finishes.

Background training:

```bash
nohup python server_scripts/train_yolo.py \
  --data-yaml /usr/src/app/yolo_dataset/data.yaml \
  --base-model /usr/src/app/yolov8n.pt \
  --output-dir /usr/src/app/runs/train \
  --device gpu \
  --epochs 100 \
  --imgsz 640 \
  --batch -1 \
  --log-file /usr/src/app/train_background.log \
  > /dev/null 2>&1 &

tail -f /usr/src/app/train_background.log
```

## Predict

```bash
python server_scripts/predict_yolo.py \
  --model /data/runs/train/train/weights/best.pt \
  --image-folder /data/images \
  --output-dir /data/runs/infer \
  --device gpu \
  --conf 0.25 \
  --iou 0.7 \
  --batch -1 \
  --label-y-offset-px 0
```

Prediction recursively scans `--image-folder` for `.jpg`, `.jpeg`, `.png`, and
`.bmp`. It does not require `mapping.json` and does not copy source images.
Use `--log-file path` to choose the log file. If omitted, the script writes
`predict.log` inside the generated `run_YYYYMMDD_HHMMSS` directory.
The script writes `inference_config.json` as soon as a run starts, writes
`classes.txt` after the model is loaded, and updates progress after each batch.
It also writes `current_batch.txt` before each batch starts, so if prediction
appears stuck you can inspect the exact image files in the active batch.
If all saved boxes are consistently a little too high during LabelImg review,
use `--label-y-offset-px` to move the saved YOLO labels down by that many source
image pixels without changing box width or height. Keep it at `0` unless this
systematic offset is visible across many predictions.
If a batch raises an error, the script logs the error and retries that batch
one image at a time; individual failures create matching `.error.txt` files
under `labels/`.

Output uses the same project inference structure:

```text
/data/runs/infer/run_YYYYMMDD_HHMMSS/
  predict.log
  inference_config.json
  classes.txt
  current_batch.txt
  labels/
```

The `labels` folder preserves the source folder's relative structure.

Background prediction:

```bash
nohup python server_scripts/predict_yolo.py \
  --model /usr/src/app/runs/detect/train_F5570/weights/best.pt \
  --image-folder /usr/src/app/server_scripts/wait_infer/5.21 \
  --output-dir /usr/src/app/server_scripts/already_infer/5.21 \
  --device gpu \
  --conf 0.05 \
  --iou 0.1 \
  --batch 32 \
  --label-y-offset-px 4 \
  --log-file /usr/src/app/server_scripts/already_infer/5.21/predict.log \
  > /dev/null 2>&1 &

tail -f /usr/src/app/server_scripts/already_infer/5.21/predict.log
```

You can also make the scripts executable on Linux:

```bash
chmod +x server_scripts/train_yolo.py server_scripts/predict_yolo.py
./server_scripts/train_yolo.py --help
./server_scripts/predict_yolo.py --help
```
