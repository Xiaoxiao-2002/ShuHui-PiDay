import { useEffect, useState } from "react";
import { registerSW } from "virtual:pwa-register";

export function UpdateBanner() {
  const [updateReady, setUpdateReady] = useState(false);
  const [update, setUpdate] = useState<((reloadPage?: boolean) => Promise<void>) | null>(null);
  useEffect(() => {
    const updateSW = registerSW({ onNeedRefresh: () => setUpdateReady(true) });
    setUpdate(() => updateSW);
  }, []);
  if (!updateReady || !update) return null;
  return (
    <div className="update-banner">
      <span>题目或程序已有新版本。</span>
      <button type="button" onClick={() => update(true)}>立即更新</button>
    </div>
  );
}
