package com.chek.auth.service;

import com.chek.auth.data.ResponseData;
import com.chek.auth.entity.dto.UserLoginDTO;
import com.chek.auth.request.WechatBindReq;
import com.chek.auth.request.WechatLoginReq;

/**
 * 微信相关认证能力
 *
 * 说明：具体对接微信 openapi、TOS 等细节按平台统一组件接入，这里只定义统一入口，便于后续扩展。
 */
public interface WechatAuthService {

    /**
     * 微信 code 登录，必要时自动创建统一用户并颁发 OAuth2 token
     */
    ResponseData<UserLoginDTO> loginByCode(WechatLoginReq req);

    /**
     * 已登录用户绑定微信
     */
    void bindWechat(Long userId, Long applicationId, WechatBindReq req);

    /**
     * 已登录用户解绑微信
     */
    void unbindWechat(Long userId, Long applicationId);
}


