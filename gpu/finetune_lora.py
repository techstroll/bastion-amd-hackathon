"""Fine-tune a per-tenant LoRA adapter ON the MI300X — data never leaves the box.

Usage (inside the ADC notebook terminal):
    python gpu/finetune_lora.py --tenant legal
    python gpu/finetune_lora.py --tenant finance

Trains a small LoRA on the tenant's private dataset (gpu/datasets/<tenant>.jsonl,
{"prompt": ..., "response": ...} per line) and saves the adapter to
/workspace/adapters/<tenant>-lora, ready for vLLM multi-LoRA serving.

This is deliberately a fast demo-scale run (few minutes on MI300X). The point
for the pitch: the SAME 192 GB GPU both trains and serves every tenant.
"""

import argparse
import json
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
    DataCollatorForLanguageModeling,
)

BASE_MODEL = "Qwen/Qwen2.5-7B-Instruct"  # ungated — no HF login/license needed
ADAPTER_DIR = Path("/workspace/adapters")
DATA_DIR = Path(__file__).resolve().parent / "datasets"
MAX_LEN = 1024


def load_tenant_dataset(tenant: str, tokenizer) -> Dataset:
    rows = []
    with open(DATA_DIR / f"{tenant}.jsonl") as f:
        for line in f:
            ex = json.loads(line)
            text = tokenizer.apply_chat_template(
                [
                    {"role": "user", "content": ex["prompt"]},
                    {"role": "assistant", "content": ex["response"]},
                ],
                tokenize=False,
            )
            rows.append({"text": text})

    ds = Dataset.from_list(rows)

    def tok(batch):
        return tokenizer(batch["text"], truncation=True, max_length=MAX_LEN)

    return ds.map(tok, batched=True, remove_columns=["text"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tenant", required=True, choices=["legal", "finance", "hr"])
    ap.add_argument("--epochs", type=int, default=3)
    args = ap.parse_args()

    out_dir = ADAPTER_DIR / f"{args.tenant}-lora"
    out_dir.mkdir(parents=True, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, torch_dtype=torch.bfloat16, device_map="cuda"
    )
    model = get_peft_model(
        model,
        LoraConfig(
            r=16,
            lora_alpha=32,
            lora_dropout=0.05,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
            task_type="CAUSAL_LM",
        ),
    )
    model.print_trainable_parameters()

    trainer = Trainer(
        model=model,
        args=TrainingArguments(
            output_dir=str(out_dir / "ckpt"),
            num_train_epochs=args.epochs,
            per_device_train_batch_size=4,
            learning_rate=2e-4,
            bf16=True,
            logging_steps=1,
            save_strategy="no",
            report_to=[],
        ),
        train_dataset=load_tenant_dataset(args.tenant, tokenizer),
        data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
    )
    trainer.train()

    model.save_pretrained(out_dir)
    tokenizer.save_pretrained(out_dir)
    print(f"\n✅ {args.tenant}-lora saved to {out_dir} — data never left the box.")


if __name__ == "__main__":
    main()
