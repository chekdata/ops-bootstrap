package com.chek.auth.request;

import lombok.Data;

import javax.validation.constraints.NotBlank;

/**
 * 场景化短信发送请求
 */
@Data
public class SmsSceneSendReq {

    @NotBlank(message = "手机号不能为空")
    private String mobilePhone;

    /**
     * 场景：LOGIN / BIND_PHONE / REGISTER / RESET_PWD 等
     */
    @NotBlank(message = "scene不能为空")
    private String scene;
}


