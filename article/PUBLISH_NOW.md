# DO THIS NOW — publish on AWS Builder Center

**Deadline:** July 13, 2026 · 1:00 PM PT  
**Prize:** First 50 **qualifying** entries → AWS Builder Jacket

You can publish **right now** using the public GitHub repo as your link.  
When AWS verification finishes, edit the article and add the live Function URL.

---

## Step-by-step (10 minutes)

### 1. Open Builder Center (Chrome)
https://builder.aws.com

Sign in with the same Builder ID / account you already set up.

### 2. Create a new **Article**

### 3. Title (must match exactly this pattern)
```
Weekend Productivity Challenge: ThreeToday
```

### 4. Tag
Add: `#productivity`

### 5. Body
Paste everything from:

`article/BODY_PASTE.md`

### 6. Links / resources
- **Repo:** https://github.com/shxkir/threetoday  
- **Live app:** (add after deploy — watcher will create `.function-url`)

### 7. Screenshots (attach these)
From `screenshots/`:
1. `01-home.png` — app home UI  
2. `02-results.png` — locked plan (today / parked / killed)  
3. `03-architecture.svg` — architecture diagram  

### 8. Publish
Hit publish. Done.

---

## After AWS unlocks (automatic)

A watcher is running. When Lambda works it will:
1. Deploy ThreeToday  
2. Save the URL to `threetoday/.function-url`  
3. Test the live API  

Then: **edit your article** and paste the Function URL under the link section.

Manual deploy if needed:
```bash
cd ~/threetoday/infra
./deploy-cli.sh
```
