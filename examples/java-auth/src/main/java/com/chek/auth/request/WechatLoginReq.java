package com.chek.auth.request;

import lombok.Data;

import javax.validation.constraints.NotBlank;

/**
 * 微信登录请求
 */
@Data
public class WechatLoginReq {

    @NotBlank(message = "code不能为空")
    private String code;

    /**
     * 在 auth-saas 注册的 clientId，用于选择 OAuth2 client
     */
    @NotBlank(message = "clientId不能为空")
    private String clientId;

    /**
     * 可选：业务侧回调标识 / 场景
     */
    private String scene;
}


