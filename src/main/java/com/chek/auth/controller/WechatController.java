package com.chek.auth.controller;

import com.chek.auth.data.ResponseData;
import com.chek.auth.entity.dto.UserLoginDTO;
import com.chek.auth.request.WechatBindReq;
import com.chek.auth.request.WechatLoginReq;
import com.chek.auth.service.WechatAuthService;
import com.chek.auth.util.ServletRequestHeaderUtils;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 微信相关接口
 */
@RestController
@RequestMapping("/v1/wechat")
@Slf4j
public class WechatController {

    @Autowired
    private WechatAuthService wechatAuthService;

    /**
     * 微信 code 登录，必要时自动创建统一用户并颁发 OAuth2 token
     */
    @PostMapping("/login")
    public ResponseData<UserLoginDTO> login(@RequestBody @Validated WechatLoginReq req) {
        return wechatAuthService.loginByCode(req);
    }

    /**
     * 已登录用户绑定微信
     */
    @PostMapping("/bind")
    public ResponseData<Object> bind(@RequestBody @Validated WechatBindReq req) {
        Long userId = ServletRequestHeaderUtils.getUserId();
        Long applicationId = ServletRequestHeaderUtils.getApplicationId();
        wechatAuthService.bindWechat(userId, applicationId, req);
        return ResponseData.success();
    }

    /**
     * 已登录用户解绑微信
     */
    @PostMapping("/unbind")
    public ResponseData<Object> unbind() {
        Long userId = ServletRequestHeaderUtils.getUserId();
        Long applicationId = ServletRequestHeaderUtils.getApplicationId();
        wechatAuthService.unbindWechat(userId, applicationId);
        return ResponseData.success();
    }
}


