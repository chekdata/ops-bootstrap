package com.chek.auth.service;

import com.chek.auth.data.ResponseData;
import com.chek.auth.request.SmsSceneSendReq;
import com.chek.auth.request.SmsSendReq;
import com.chek.auth.request.SmsVerifyReq;

/**
 * 验证码接口（包含登录及通用场景）
 */
public interface CheckCodeService {

    /**
     * 发送内部用户登录验证码（历史接口，保留兼容）
     */
    ResponseData<Object> sendUserLoginCode(SmsSendReq request);

    /**
     * 按场景发送验证码（LOGIN / BIND_PHONE / REGISTER / RESET_PWD 等）
     */
    ResponseData<Object> sendWithScene(SmsSceneSendReq request);

    /**
     * 按场景校验验证码
     */
    boolean verifyWithScene(SmsVerifyReq request);
}


