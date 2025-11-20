package com.chek.auth.service.impl;

import com.chek.auth.constant.SysCommonConstant;
import com.chek.auth.data.ResponseData;
import com.chek.auth.entity.dto.SendSmsDTO;
import com.chek.auth.request.SmsSceneSendReq;
import com.chek.auth.request.SmsSendReq;
import com.chek.auth.request.SmsVerifyReq;
import com.chek.auth.service.CheckCodeService;
import com.chek.auth.service.SmsSendService;
import com.chek.auth.util.SequenceUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.util.concurrent.TimeUnit;

/**
 * 验证码接口实现（登录 + 通用场景）
 */
@Service
@Slf4j
public class CheckCodeServiceImpl implements CheckCodeService {

    private static final int EXPIRE_TIME = 300;

    @Autowired
    private SmsSendService smsSendService;

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    @Override
    public ResponseData<Object> sendUserLoginCode(SmsSendReq request) {
        String mobilePhone = request.getMobilePhone();
        String realKey = SysCommonConstant.USER_LOGIN_CHECK_CODE_REDIS_KEY_HEAD + mobilePhone;
        return commonSend(mobilePhone, request.getTemplateCode(), realKey, request.getExpireTime());
    }

    @Override
    public ResponseData<Object> sendWithScene(SmsSceneSendReq request) {
        String mobilePhone = request.getMobilePhone();
        String scene = request.getScene();
        String redisKey = buildSceneKey(mobilePhone, scene);
        // 模板编码后续可从配置中心映射，这里先给出合理默认
        String templateCode = "LOGIN".equalsIgnoreCase(scene) ? "LOGIN_CODE" : "COMMON_CODE";
        return commonSend(mobilePhone, templateCode, redisKey, null);
    }

    @Override
    public boolean verifyWithScene(SmsVerifyReq request) {
        String mobilePhone = request.getMobilePhone();
        String scene = request.getScene();
        String redisKey = buildSceneKey(mobilePhone, scene);
        Object cached = redisTemplate.opsForValue().get(redisKey);
        if (cached == null) {
            return false;
        }
        boolean ok = request.getCode().equals(String.valueOf(cached));
        if (ok) {
            redisTemplate.delete(redisKey);
        }
        return ok;
    }

    private ResponseData<Object> commonSend(String mobilePhone, String templateCode, String realKey, Integer expireTime) {
        SendSmsDTO sendSmsDTO = new SendSmsDTO();
        sendSmsDTO.setPhoneNumbers(mobilePhone);
        // 生成随机验证码
        String checkCode = SequenceUtil.randomNo(6);
        sendSmsDTO.setTemplateCode(templateCode);
        sendSmsDTO.setTemplateParam("{\"code\":\"" + checkCode + "\"}");
        sendSmsDTO.setSignName(SysCommonConstant.SIGN_NAME);
        // 将获取的验证码存入redis中
        redisTemplate.opsForValue().set(realKey, checkCode,
                expireTime != null ? expireTime : EXPIRE_TIME, TimeUnit.SECONDS);
        return smsSendService.doSend(sendSmsDTO);
    }

    private String buildSceneKey(String mobilePhone, String scene) {
        String prefix = SysCommonConstant.CHECK_CODE_REDIS_KEY_HEAD;
        if ("LOGIN".equalsIgnoreCase(scene)) {
            prefix = SysCommonConstant.USER_LOGIN_CHECK_CODE_REDIS_KEY_HEAD;
        } else if ("BIND_PHONE".equalsIgnoreCase(scene)) {
            prefix = SysCommonConstant.CHECK_CODE_REDIS_KEY_HEAD + "bindPhone:";
        } else if ("REGISTER".equalsIgnoreCase(scene)) {
            prefix = SysCommonConstant.CHECK_CODE_REDIS_KEY_HEAD + "register:";
        } else if ("RESET_PWD".equalsIgnoreCase(scene)) {
            prefix = SysCommonConstant.CHECK_CODE_REDIS_KEY_HEAD + "resetPwd:";
        }
        return prefix + mobilePhone;
    }
}


