package com.chek.auth.service.impl;

import com.chek.auth.data.ResponseData;
import com.chek.auth.entity.User;
import com.chek.auth.entity.dto.UserLoginDTO;
import com.chek.auth.exception.CustomException;
import com.chek.auth.request.WechatBindReq;
import com.chek.auth.request.WechatLoginReq;
import com.chek.auth.service.LoginService;
import com.chek.auth.service.UserService;
import com.chek.auth.service.WechatAuthService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

/**
 * 微信认证相关实现
 *
 * 说明：
 * - 这里先实现最小闭环：通过 code 换取 openid/unionid 的逻辑后续接入统一微信组件；
 * - 当前实现只做用户查找/创建 + 调用现有 LoginService 颁发 token，避免复制 OAuth2 逻辑。
 */
@Service
@Slf4j
public class WechatAuthServiceImpl implements WechatAuthService {

    @Autowired
    private UserService userService;

    @Autowired
    private LoginService loginService;

    @Override
    public ResponseData<UserLoginDTO> loginByCode(WechatLoginReq req) {
        // TODO: 接入统一微信组件：根据 code 换取 unionid/openid
        // 目前先占位抛错，避免误用未接通微信配置的环境
        throw new CustomException("微信登录暂未开放，请联系平台配置微信应用后再试");
    }

    @Override
    public void bindWechat(Long userId, Long applicationId, WechatBindReq req) {
        // TODO: 接入统一微信组件，写入 unionid 等信息到用户扩展字段
        throw new CustomException("微信绑定暂未开放，请联系平台配置微信应用后再试");
    }

    @Override
    public void unbindWechat(Long userId, Long applicationId) {
        // TODO: 清理用户扩展字段中的 unionid 等绑定信息
        throw new CustomException("微信解绑暂未开放，请联系平台配置微信应用后再试");
    }
}


