import json
import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers.models.bert.modeling_bert import BertPreTrainedModel, BertEmbeddings, BertModel

from utils.swin_trt import swin_tiny
# from utils.deit import deit_base_patch16_LS as deit
from utils.modeling import LXRTEncoder, LXRTModel, LXRTFeatureExtraction
from category_id_map import CATEGORY_ID_LIST


class LXMERT(nn.Module):
    def __init__(self, args):
        super().__init__()
        self.visual_backbone = swin_tiny(args.swin_pretrained_path)
        # self.nextvlad = NeXtVLAD(args.frame_embedding_size, args.vlad_cluster_size,
        #                          output_size=args.vlad_hidden_size, dropout=args.dropout)
        # self.enhance = SENet(channels=args.vlad_hidden_size, ratio=args.se_ratio)
        self.video_dense = nn.Linear(768, 768)

        self.encoder = LXRTFeatureExtraction.from_pretrained(args.bert_dir, cache_dir=args.bert_cache)

        # self.fusion = ConcatDenseSE(768, 768, args.se_ratio, args.dropout)
        # self.encoder = Bert_encoder.from_pretrained(args.bert_dir, cache_dir=args.bert_cache)
        # self.classifier = nn.Linear(args.fc_size, len(CATEGORY_ID_LIST))
        # self.classifier = nn.Sequential(
        #           nn.Linear(768, 768),
        #           nn.ReLU(),
        #           nn.Linear(768, len(CATEGORY_ID_LIST))
        #         )
        self.drop = nn.Dropout(p=0.3)
        self.classifier = nn.Linear(768, len(CATEGORY_ID_LIST))
# self.classifier = nn.Sequential(
        #           nn.Linear(768, 768),
        #           nn.ReLU(),
        #           nn.Linear(768, len(CATEGORY_ID_LIST))
        #         )
    def forward(self, frame_input, frame_mask, text_input, text_mask, label=1, inference=False):
        frame_inputs = self.visual_backbone(frame_input)

        # frame_fea = self.nextvlad(frame_inputs, frame_mask)
        # frame_fea = self.enhance(frame_fea)
        frame_fea = self.video_dense(frame_inputs)

        encoder_outputs = self.encoder(input_ids=text_input, attention_mask=text_mask, visual_feats=frame_fea, visual_attention_mask=frame_mask)
        output = self.drop(encoder_outputs)
        prediction = self.classifier(output)

        if inference:
            return torch.argmax(prediction, dim=1)
        else:
            return self.cal_loss(prediction, label)

    @staticmethod
    def cal_loss(prediction, label):
        label = label.squeeze(dim=1)
        loss = F.cross_entropy(prediction, label, label_smoothing=0.1)
        with torch.no_grad():
            pred_label_id = torch.argmax(prediction, dim=1)
            accuracy = (label == pred_label_id).float().sum() / label.shape[0]
        return loss, accuracy, pred_label_id, label