//+------------------------------------------------------------------+
//| FxCopier.mq5                                                     |
//| Telegram channel -> MT5 auto trader (polls local bridge)          |
//+------------------------------------------------------------------+
#property strict

#include <Trade/Trade.mqh>

input string InpBridgeUrl = "http://127.0.0.1:8000/latest";
input int    InpPollSeconds = 5;
input double InpLots = 0.10;
input long   InpMagic = 88001;
input int    InpMaxSpreadPoints = 80; // adjust per broker/symbol

CTrade trade;
long last_msg_id = -1;

// Minimal JSON extraction helpers (string-based, MVP)
string JsonGetString(const string json, const string key)
{
   string pat = '"' + key + '"';
   int p = StringFind(json, pat);
   if(p < 0) return "";
   p = StringFind(json, ":", p);
   if(p < 0) return "";
   // skip spaces
   while(p < (int)StringLen(json) && (StringGetCharacter(json, p) == ':' || StringGetCharacter(json, p) == ' ')) p++;
   if(p >= (int)StringLen(json)) return "";
   if(StringGetCharacter(json, p) != '"') return "";
   p++;
   int e = StringFind(json, "\"", p);
   if(e < 0) return "";
   return StringSubstr(json, p, e - p);
}

double JsonGetNumber(const string json, const string key, bool &ok)
{
   ok = false;
   string pat = '"' + key + '"';
   int p = StringFind(json, pat);
   if(p < 0) return 0.0;
   p = StringFind(json, ":", p);
   if(p < 0) return 0.0;
   p++;
   while(p < (int)StringLen(json) && (StringGetCharacter(json, p) == ' ')) p++;

   int e = p;
   while(e < (int)StringLen(json))
   {
      ushort c = StringGetCharacter(json, e);
      if((c >= '0' && c <= '9') || c == '.' || c == '-') { e++; continue; }
      break;
   }
   if(e == p) return 0.0;
   ok = true;
   return StringToDouble(StringSubstr(json, p, e - p));
}

long JsonGetLong(const string json, const string key, bool &ok)
{
   ok = false;
   bool nok=false;
   double v = JsonGetNumber(json, key, nok);
   if(!nok) return 0;
   ok = true;
   return (long)v;
}

bool HttpGet(const string url, string &out)
{
   char result[];
   string headers;
   char post[];
   ResetLastError();
   int timeout = 5000;
   int res = WebRequest("GET", url, headers, timeout, post, 0, result, headers);
   if(res == -1)
   {
      Print("WebRequest failed. err=", GetLastError(), ". Add URL in MT5 Options -> Expert Advisors.");
      return false;
   }
   out = CharArrayToString(result, 0, ArraySize(result));
   return true;
}

bool SpreadOk(const string sym)
{
   long spread = 0;
   if(!SymbolInfoInteger(sym, SYMBOL_SPREAD, spread)) return true;
   return (spread <= InpMaxSpreadPoints);
}

int OnInit()
{
   trade.SetExpertMagicNumber((uint)InpMagic);
   EventSetTimer(InpPollSeconds);
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   EventKillTimer();
}

void OnTimer()
{
   string json;
   if(!HttpGet(InpBridgeUrl, json)) return;

   bool ok=false;
   long msg_id = JsonGetLong(json, "msg_id", ok);
   if(!ok || msg_id <= 0) return;
   if(msg_id == last_msg_id) return;

   // Extract nested signal fields by searching within "signal":{...}
   int ps = StringFind(json, "\"signal\"");
   if(ps < 0) return;

   string side = JsonGetString(json, "side");
   string symbol = JsonGetString(json, "symbol");

   bool sl_ok=false;
   double sl = JsonGetNumber(json, "sl", sl_ok);

   // TP: take first tp if present
   double tp = 0.0;
   int ptp = StringFind(json, "\"tp\"");
   if(ptp >= 0)
   {
      int b1 = StringFind(json, "[", ptp);
      int b2 = StringFind(json, "]", ptp);
      if(b1 > 0 && b2 > b1)
      {
         string arr = StringSubstr(json, b1+1, b2-b1-1);
         // first number until comma
         int comma = StringFind(arr, ",");
         string first = (comma>0? StringSubstr(arr,0,comma):arr);
         first = StringTrim(first);
         tp = StringToDouble(first);
      }
   }

   if(symbol == "" || (side != "BUY" && side != "SELL"))
      return;

   if(!SymbolSelect(symbol, true))
   {
      Print("SymbolSelect failed: ", symbol);
      return;
   }

   if(!SpreadOk(symbol))
   {
      Print("Spread too high for ", symbol, ", skipping");
      return;
   }

   // Place trade
   bool placed=false;
   if(side == "BUY")
   {
      placed = trade.Buy(InpLots, symbol, 0.0, sl_ok?sl:0.0, tp>0?tp:0.0, "FxCopier");
   }
   else
   {
      placed = trade.Sell(InpLots, symbol, 0.0, sl_ok?sl:0.0, tp>0?tp:0.0, "FxCopier");
   }

   if(placed)
   {
      last_msg_id = msg_id;
      Print("Placed ", side, " ", symbol, " from msg_id=", msg_id);
   }
   else
   {
      Print("Order failed. retcode=", trade.ResultRetcode(), " desc=", trade.ResultRetcodeDescription());
   }
}
