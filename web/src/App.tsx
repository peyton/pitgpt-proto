import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AppProvider } from "./lib/AppContext";
import { Layout } from "./components/Layout";
import { Home } from "./pages/Home";
import { ProtocolReview } from "./pages/ProtocolReview";
import { ActiveTrial } from "./pages/ActiveTrial";
import { Results } from "./pages/Results";
import { Settings } from "./pages/Settings";

export default function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Home />} />
            <Route path="protocol" element={<ProtocolReview />} />
            <Route path="trial" element={<ActiveTrial />} />
            <Route path="results" element={<Results />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AppProvider>
  );
}
