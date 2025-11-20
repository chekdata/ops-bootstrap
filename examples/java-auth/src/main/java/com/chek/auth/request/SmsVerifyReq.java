package com.chek.auth.request;

import lombok.Data;

import javax.validation.constraints.NotBlank;

/**
 * 场景化短信验证码校验请求
 */
@Data
public class SmsVerifyReq {

    @NotBlank(message = "手机号不能为空")
    private String mobilePhone;

    @NotBlank(message = "验证码不能为空")
    private String code;

    @NotBlank(message = "scene不能为空")
    private String scene;
}


