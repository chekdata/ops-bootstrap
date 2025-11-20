package com.chek.auth.request;

import lombok.Data;

import javax.validation.constraints.NotBlank;

/**
 * 已登录用户绑定微信请求
 */
@Data
public class WechatBindReq {

    @NotBlank(message = "code不能为空")
    private String code;
}


