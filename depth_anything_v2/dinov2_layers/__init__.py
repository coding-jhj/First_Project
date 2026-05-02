# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
#
# DINOv2 Vision Transformer 구성 레이어 패키지 — dinov2.py에서 import해서 사용
# Mlp: 피드포워드 / PatchEmbed: 이미지→패치 / SwiGLUFFN: 게이팅 FFN / MemEffAttention: 메모리 효율적 어텐션

from .mlp import Mlp                                    # 표준 MLP 피드포워드 레이어
from .patch_embed import PatchEmbed                     # 이미지를 패치 임베딩으로 변환
from .swiglu_ffn import SwiGLUFFN, SwiGLUFFNFused       # SwiGLU 활성화 함수 기반 FFN
from .block import NestedTensorBlock                    # ViT 트랜스포머 블록 (어텐션+FFN)
from .attention import MemEffAttention                  # xFormers 기반 메모리 효율적 멀티헤드 어텐션
