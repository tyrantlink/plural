# Automod

This page is intended for server moderators

### Automod Blocking Masked Links
/plu/ral userproxy messages are **not** compatible with automod rules that block masked links, as masked links are used when replying to a message.


#### Solutions
1. Educate yourself and your members, and disable the automod rule
  - If you're worried about malicious links, you should be worried about all links, not just masked ones, any person can send a malicious link, masked or not, servers should be moderated and members should be educated.
  - Masked links are a native discord feature, and not inherently malicious.
  - Discord has a built-in pop-up to warn you about the website you're about to visit when clicking a link
  - Educate members to ping a staff member if they're unsure about a link, and to not click on links from people they don't trust.
  - Disabling the masked link feature as a whole is pointlessly restrictive, and will only serve to annoy your members.
2. Use a more leinent automod rule
  - Read all the points in the first solution, and consider them first.
  - If you decide you still want to block some malicious links, consider the following regex pattern
```regex
\[[^\]\.]+\.[^\]]+]\(<?\S+://.+>?\)
```
  - This pattern will *only* block masked links that pretend to be their own links
  - For example, `[steam.com/freegift](https://discord.gg/4mteVXBDW7)` would be blocked
  - And `[the development server](https://discord.gg/4mteVXBDW7)` would not be blocked
3. Create a bypass role
  - If your server has some kind of leveling bot, allow the active members to bypass the automod rule
  - If you're stubborn and don't trust your members, you can create a role that bypasses the automod rule, and give it to members that use /plu/ral userproxies
  - If you still want to block some links, consider making two rules, one that blocks all masked links, and one that only blocks likely malicious links, then set the bypass role to bypass the first rule, but not the second.
  - In this scenario, users with the bypass role can still send some masked links, just not the malicious ones, and users without the role can't send any masked links.