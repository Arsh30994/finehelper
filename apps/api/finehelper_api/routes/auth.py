from __future__ import annotations

from fastapi import APIRouter, Request

from finehelper_api.controllers import auth_controller
from finehelper_api.deps import AuthDep, DbDep, SettingsDep
from finehelper_api.schemas import (
    BiometricRegisterIn,
    BiometricUnlockIn,
    LoginIn,
    OtpVerifyIn,
    PhoneIn,
    SignupIn,
    TokenOut,
)

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/signup", response_model=TokenOut)
async def signup(body: SignupIn, request: Request, db: DbDep, settings: SettingsDep):
    return await auth_controller.signup(db, settings, body, request)


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, request: Request, db: DbDep, settings: SettingsDep):
    return await auth_controller.login(db, settings, body, request)


@router.get("/me")
async def me(auth: AuthDep):
    return auth_controller.me(auth)


@router.post("/api-keys")
async def create_api_key(auth: AuthDep, db: DbDep, name: str = "cli"):
    return await auth_controller.create_api_key(db, auth, name)


@router.get("/api-keys")
async def list_api_keys(auth: AuthDep, db: DbDep):
    return await auth_controller.list_api_keys(db, auth)


@router.get("/security")
async def security_status(auth: AuthDep, db: DbDep):
    return await auth_controller.security_status(db, auth)


@router.post("/verify/email/send")
async def send_email_otp(request: Request, auth: AuthDep, db: DbDep, settings: SettingsDep):
    return await auth_controller.send_email_otp(db, settings, auth, request)


@router.post("/verify/email")
async def verify_email_otp(body: OtpVerifyIn, request: Request, auth: AuthDep, db: DbDep):
    return await auth_controller.verify_email_otp(db, auth, body, request)


@router.post("/verify/phone")
async def set_phone(body: PhoneIn, auth: AuthDep, db: DbDep):
    return await auth_controller.set_phone(db, auth, body)


@router.post("/verify/phone/send")
async def send_phone_otp(request: Request, auth: AuthDep, db: DbDep, settings: SettingsDep):
    return await auth_controller.send_phone_otp(db, settings, auth, request)


@router.post("/verify/phone/confirm")
async def verify_phone_otp(body: OtpVerifyIn, request: Request, auth: AuthDep, db: DbDep):
    return await auth_controller.verify_phone_otp(db, auth, body, request)


@router.get("/biometric/challenge")
async def biometric_challenge(auth: AuthDep, db: DbDep):
    return await auth_controller.biometric_status(db, auth)


@router.post("/biometric/register")
async def biometric_register(body: BiometricRegisterIn, auth: AuthDep, db: DbDep):
    return await auth_controller.biometric_register(db, auth, body)


@router.post("/biometric/unlock")
async def biometric_unlock(body: BiometricUnlockIn, auth: AuthDep, db: DbDep):
    return await auth_controller.biometric_unlock(db, auth, body)
