import { Route, Routes } from "react-router";

import { Shell } from "./components/Shell";
import { GroupsPage } from "./pages/GroupsPage";
import { ImportPage } from "./pages/ImportPage";
import { MapPage } from "./pages/MapPage";
import { QualityPage } from "./pages/QualityPage";
import { ReportPage } from "./pages/ReportPage";
import { ThresholdPage } from "./pages/ThresholdPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route path="/" element={<ImportPage />} />
        <Route path="/datasets/:datasetId/map" element={<MapPage />} />
        <Route path="/audits/:auditId/quality" element={<QualityPage />} />
        <Route path="/audits/:auditId/groups" element={<GroupsPage />} />
        <Route path="/audits/:auditId/threshold" element={<ThresholdPage />} />
        <Route path="/audits/:auditId/report" element={<ReportPage />} />
      </Route>
    </Routes>
  );
}
