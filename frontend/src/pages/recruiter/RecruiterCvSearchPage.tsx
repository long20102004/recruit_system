import { RecruiterLayout } from "../../components/common";
import { DiscoverableCvSearch } from "./DiscoverableCvSearch";

export function RecruiterCvSearchPage() {
  return <RecruiterLayout active="cvSearch">
    <DiscoverableCvSearch />
  </RecruiterLayout>;
}
