import torch
import torch.nn.functional as F
import torch.nn as nn
import numpy as np
from .MCLEA_tools import MultiModalEncoder
from .MCLEA_loss import CustomMultiLossLayer, ial_loss, icl_loss
from src.utils import pairwise_distances
from geea import GEEA
import pickle


class MCLEA(nn.Module):
    def __init__(self, kgs, args):
        super().__init__()
        self.kgs = kgs
        self.args = args
        self.img_features = F.normalize(
            torch.FloatTensor(kgs["images_list"])).cuda()
        self.input_idx = kgs["input_idx"].cuda()
        self.adj = kgs["adj"].cuda()
        self.rel_features = torch.Tensor(kgs["rel_features"]).cuda()
        self.att_features = torch.Tensor(kgs["att_features"]).cuda()
        self.name_features = None
        self.char_features = None
        if kgs["name_features"] is not None:
            self.name_features = kgs["name_features"].cuda()
            self.char_features = kgs["char_features"].cuda()

        img_dim = self._get_img_dim(kgs)

        char_dim = kgs["char_features"].shape[1] if self.char_features is not None else 100


        self.multimodal_encoder = MultiModalEncoder(args=self.args,
                                                    ent_num=kgs["ent_num"],
                                                    img_feature_dim=img_dim,
                                                    char_feature_dim=char_dim,
                                                    use_project_head=self.args.use_project_head,
                                                    attr_input_dim=kgs["att_features"].shape[1])

        self.multi_loss_layer = CustomMultiLossLayer(loss_num=6)  # 6
        self.align_multi_loss_layer = CustomMultiLossLayer(loss_num=6)  # 6

        self.criterion_cl = icl_loss(
            tau=self.args.tau, ab_weight=self.args.ab_weight, n_view=2)
        self.criterion_align = ial_loss(tau=self.args.tau2,
                                        ab_weight=self.args.ab_weight,
                                        zoom=self.args.zoom,
                                        reduction=self.args.reduction)

        self.concrete_features = [self.adj.cpu().to_dense(), self.img_features, self.rel_features, self.att_features,
                                   self.name_features, self.char_features]

        self.geea = GEEA(args, kgs, self.concrete_features,
                         sub_dims=[self.multimodal_encoder.n_units[-1], self.args.img_dim, self.args.attr_dim, self.args.attr_dim,
                          self.args.name_dim, self.args.char_dim], joint_dim=self.multimodal_encoder.n_units[-1], ent_embs=self.multimodal_encoder.entity_emb.weight,
                         fusion_layer=self.multimodal_encoder)
        


    def forward(self, batch):
        gph_emb, img_emb, rel_emb, att_emb, name_emb, char_emb, joint_emb = self.joint_emb_generat(
            only_joint=False)
        
        #  ICL loss for joint embedding
        loss_joi = self.criterion_cl(joint_emb, batch)
        # ICL loss for uni-modal embedding
        in_loss = self.inner_view_loss(
            gph_emb, rel_emb, att_emb, img_emb, name_emb, char_emb, batch)

        # IAL loss for uni-modal embedding
        align_loss = self.kl_alignment_loss(
            joint_emb, gph_emb, rel_emb, att_emb, img_emb, name_emb, char_emb, batch)

        
        loss_all = 0.
        loss_all += loss_joi + in_loss + align_loss

        geea_loss = self.geea(batch, [gph_emb, img_emb, rel_emb, att_emb, name_emb, char_emb], joint_emb)

        with open('joint_emb', 'wb') as f:
            pickle.dump(joint_emb, f)
        loss_all += geea_loss

        weight_raw = self.multimodal_encoder.fusion.weight.reshape(-1).tolist()
        loss_dic = {"joint_Intra_modal": loss_joi.item(
        ), "Intra_modal": in_loss.item(), "Inter_modal": align_loss.item()}
        output = {"loss_dic": loss_dic, "emb": joint_emb, "weight": weight_raw}
        return loss_all, output

    def inner_view_loss(self, gph_emb, rel_emb, att_emb, img_emb, name_emb, char_emb, train_ill):

        loss_GCN = self.criterion_cl(
            gph_emb, train_ill) if gph_emb is not None else 0
        loss_rel = self.criterion_cl(
            rel_emb, train_ill) if rel_emb is not None else 0
        loss_att = self.criterion_cl(
            att_emb, train_ill) if att_emb is not None else 0
        loss_img = self.criterion_cl(
            img_emb, train_ill) if img_emb is not None else 0
        loss_name = self.criterion_cl(
            name_emb, train_ill) if name_emb is not None else 0
        loss_char = self.criterion_cl(
            char_emb, train_ill) if char_emb is not None else 0

        total_loss = self.multi_loss_layer(
            [loss_GCN, loss_rel, loss_att, loss_img, loss_name, loss_char])
        return total_loss

    def kl_alignment_loss(self, joint_emb, gph_emb, rel_emb, att_emb, img_emb, name_emb, char_emb, train_ill):
        zoom = self.args.zoom
        loss_GCN = self.criterion_align(
            gph_emb, joint_emb, train_ill) if gph_emb is not None else 0
        loss_rel = self.criterion_align(
            rel_emb, joint_emb, train_ill) if rel_emb is not None else 0
        loss_att = self.criterion_align(
            att_emb, joint_emb, train_ill) if att_emb is not None else 0
        loss_img = self.criterion_align(
            img_emb, joint_emb, train_ill) if img_emb is not None else 0
        loss_name = self.criterion_align(
            name_emb, joint_emb, train_ill) if name_emb is not None else 0
        loss_char = self.criterion_align(
            char_emb, joint_emb, train_ill) if char_emb is not None else 0

        total_loss = self.align_multi_loss_layer(
            [loss_GCN, loss_rel, loss_att, loss_img, loss_name, loss_char]) * zoom
        return total_loss


    def joint_emb_generat(self, only_joint=True):
        gph_emb, img_emb, rel_emb, att_emb, name_emb, char_emb = self.multimodal_encoder._emb_generate(self.input_idx,
                                                                                                       self.adj,
                                                                                                       self.img_features,
                                                                                                       self.rel_features,
                                                                                                       self.att_features,
                                                                                                       self.name_features,
                                                                                                       self.char_features)

        joint_emb = self.multimodal_encoder(
            gph_emb, img_emb, rel_emb, att_emb, name_emb, char_emb)

        if only_joint:
            return joint_emb
        else:
            return gph_emb, img_emb, rel_emb, att_emb, name_emb, char_emb, joint_emb



    def _get_img_dim(self, kgs):
        if isinstance(kgs["images_list"], list):
            img_dim = kgs["images_list"][0].shape[1]
        elif isinstance(kgs["images_list"], np.ndarray) or torch.is_tensor(kgs["images_list"]):
            img_dim = kgs["images_list"].shape[1]
        return img_dim

    def Iter_new_links(self, epoch, left_non_train, final_emb, right_non_train, new_links=[]):
        if len(left_non_train) == 0 or len(right_non_train) == 0:
            return new_links
        distance_list = []
        for i in np.arange(0, len(left_non_train), 1000):
            d = pairwise_distances(
                final_emb[left_non_train[i:i + 1000]], final_emb[right_non_train])
            distance_list.append(d)
        distance = torch.cat(distance_list, dim=0)
        preds_l = torch.argmin(distance, dim=1).cpu().numpy().tolist()
        preds_r = torch.argmin(distance.t(), dim=1).cpu().numpy().tolist()
        del distance_list, distance, final_emb
        if (epoch + 1) % (self.args.semi_learn_step * 10) == self.args.semi_learn_step:
            new_links = [(left_non_train[i], right_non_train[p])
                         for i, p in enumerate(preds_l) if preds_r[p] == i]
        else:
            new_links = [(left_non_train[i], right_non_train[p]) for i, p in enumerate(preds_l) if (
                preds_r[p] == i) and ((left_non_train[i], right_non_train[p]) in new_links)]


        return new_links

    def data_refresh(self, logger, train_ill, test_ill_, left_non_train, right_non_train, new_links=[]):
        if len(new_links) != 0 and (len(left_non_train) != 0 and len(right_non_train) != 0):
            new_links_select = new_links
            train_ill = np.vstack((train_ill, np.array(new_links_select)))
            num_true = len([nl for nl in new_links_select if nl in test_ill_])
            for nl in new_links_select:
                left_non_train.remove(nl[0])
                right_non_train.remove(nl[1])

            if self.args.rank == 0:
                logger.info(f"#new_links_select:{len(new_links_select)}")
                logger.info(f"train_ill.shape:{train_ill.shape}")
                logger.info(f"#true_links: {num_true}")
                logger.info(
                    f"true link ratio: {(100 * num_true / len(new_links_select)):.1f}%")
                logger.info(
                    f"#entity not in train set: {len(left_non_train)} (left) {len(right_non_train)} (right)")

            new_links = []
        else:
            logger.info("len(new_links) is 0")

        return left_non_train, right_non_train, train_ill, new_links
