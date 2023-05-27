import logging
from typing import Optional, Union

import discord
from discord.ext import commands
from pavlov import PavlovRCON

from bot.utils import servers, user_action_log

RCON_TIMEOUT = 60

MODERATOR_ROLE = ""
CAPTAIN_ROLE = ""

SUPER_MODERATOR = [""]
SUPER_CAPTAIN = [""]


async def check_banned(ctx):
    pass


async def check_role_perms(
        ctx,
        array_name,
        server,
):
    guild_roles = await ctx.guild.fetch_roles()
    for role in server.get(array_name, []):
        logging.info(f"Checking {role}...")
        roleObj = False
        for grole in guild_roles:
            logging.info(f"Checking if {grole.id} == {role}")
            if grole.id == role:
                logging.info("THE ROLE TO CHECK HAS BEEN FOUND IN THE CURRENT GUILD'S ROLES.")
                roleObj = grole
        logging.info(roleObj)
        if roleObj:
            logging.info(f"{role} ({roleObj}) exists...")
            logging.info(roleObj.members)
            async for member in ctx.guild.fetch_members():
                if roleObj in member.roles:
                    logging.info(f"Checking if {member} == {ctx.author.id}...")
                    if ctx.author.id == member.id:
                        logging.info(f"{ctx.author.id} was found to be a member of role {role}!")
                        return True

async def check_perm_admin(
    ctx, server_name: str = None, sub_check: bool = False, global_check: bool = False
):
    """Admin permissions are stored per server in the servers.json"""
    if not server_name and not global_check:
        return False
    _servers = list()
    if server_name:
        _servers.append(servers.get(server_name))
    elif global_check:
        _servers = servers.get_servers().values()
    for server in _servers:
        logging.info("Checking members of every admin role...")
        inRoleArray = await check_role_perms(ctx, "admin_roles", server)
        if inRoleArray:
            return True
        logging.info("Checking if user is present in the admin role array...")
        if ctx.author.id in server.get("admins", []):
            logging.info(f"User {ctx.author.id} found in admin array!")
            return True
        else:
            logging.info(f"User {ctx.author.id} not found in admin array...")
    if not sub_check:
        user_action_log(
            ctx,
            f"ADMIN CHECK FAILED server={server_name}, global_check={global_check}",
            log_level=logging.WARNING,
        )
        if hasattr(ctx, "batch_exec"):
            if not ctx.batch_exec:
                await ctx.send(embed=discord.Embed(description=f"This command is only for Admins."))
    return False


def check_has_any_role(
    ctx,
    super_roles: list,
    role_format: str,
    server_name: str = None,
    global_check: bool = True,
):
    for super_role in super_roles:
        super_role = discord.utils.get(ctx.author.roles, name=super_role)
        if super_role is not None:
            return True

    role_names = list()
    if global_check:
        for server_name in servers.get_names():
            role_names.append(role_format.format(server_name))
    elif server_name:
        role_names.append(role_format.format(server_name))

    for role_name in role_names:
        r = discord.utils.get(ctx.author.roles, name=role_name)
        if r is not None:
            return True
    return False


async def check_perm_moderator(
    ctx, server_name: str = None, sub_check: bool = False, global_check: bool = False
):
    if await check_perm_admin(ctx, server_name, sub_check=True, global_check=global_check):
        return True
    inRoleArray = await check_role_perms(ctx, "mod_roles", server)
    if inRoleArray:
        return True
    if not check_has_any_role(ctx, SUPER_MODERATOR, MODERATOR_ROLE, server_name, global_check):
        if not sub_check:
            user_action_log(
                ctx,
                f"MOD CHECK FAILED server={server_name}, global_check={global_check}",
                log_level=logging.WARNING,
            )
            if hasattr(ctx, "batch_exec"):
                if not ctx.batch_exec:
                    await ctx.send(
                        embed=discord.Embed(
                            description=f"This command is only for Moderators and above."
                        )
                    )
        return False
    return True


async def check_perm_captain(ctx, server_name: str = None, global_check: bool = False):
    if await check_perm_moderator(ctx, server_name, sub_check=True, global_check=global_check):
        return True
    inRoleArray = await check_role_perms(ctx, "trialmod_roles", server)
    if inRoleArray:
        return True		
    if not check_has_any_role(ctx, SUPER_CAPTAIN, CAPTAIN_ROLE, server_name, global_check):
        user_action_log(
            ctx,
            f"CAPTAIN CHECK FAILED server={server_name} global_check={global_check}",
            log_level=logging.WARNING,
        )
        if hasattr(ctx, "batch_exec"):
            if not ctx.batch_exec:
                await ctx.send(
                    embed=discord.Embed(description=f"This command is only for Captains and above.")
                )
        return False
    return True


async def exec_server_command(
    ctx: Optional[Union[commands.Context, PavlovRCON]], server_name: str, command: str
) -> [dict, Optional[PavlovRCON]]:
    pavlov = None
    if ctx is not None and isinstance(ctx, commands.Context):
        if hasattr(ctx, "pavlov"):
            pavlov = ctx.pavlov.get(server_name)
        if pavlov is None:
            server = servers.get(server_name)
            pavlov = PavlovRCON(
                server.get("ip"),
                server.get("port"),
                server.get("password"),
                timeout=RCON_TIMEOUT,
            )
            if not hasattr(ctx, "pavlov"):
                ctx.pavlov = {server_name: pavlov}
            else:
                ctx.pavlov[server_name] = pavlov
        data = await pavlov.send(command)
        return data, ctx
    if ctx is None:
        server = servers.get(server_name)
        pavlov = PavlovRCON(
            server.get("ip"),
            server.get("port"),
            server.get("password"),
            timeout=RCON_TIMEOUT,
        )
    elif isinstance(ctx, PavlovRCON):
        pavlov = ctx
    data = await pavlov.send(command)
    return data, pavlov
