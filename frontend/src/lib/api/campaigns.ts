import {
  campaignDetail,
  campaignList,
  campaignVersion,
  createCampaignRequest,
  createCampaignResponse,
  versionDiff,
  versionList,
  type CreateCampaignInput,
  type CreateCampaignResult,
} from "@/lib/schemas";
import { apiRequest } from "./client";

export async function createCampaign(
  input: CreateCampaignInput,
  signal?: AbortSignal,
): Promise<CreateCampaignResult> {
  return apiRequest("/campaigns", createCampaignResponse, {
    method: "POST",
    body: createCampaignRequest.parse(input),
    signal,
  });
}

export function listCampaigns(signal?: AbortSignal) {
  return apiRequest("/campaigns", campaignList, { signal });
}

export function getCampaign(campaignId: string, signal?: AbortSignal) {
  return apiRequest(
    `/campaigns/${encodeURIComponent(campaignId)}`,
    campaignDetail,
    { signal },
  );
}

export function listVersions(campaignId: string, signal?: AbortSignal) {
  return apiRequest(
    `/campaigns/${encodeURIComponent(campaignId)}/versions`,
    versionList,
    { signal },
  );
}

export function getVersion(
  campaignId: string,
  version: number,
  signal?: AbortSignal,
) {
  return apiRequest(
    `/campaigns/${encodeURIComponent(campaignId)}/versions/${version}`,
    campaignVersion,
    { signal },
  );
}

export function getVersionDiff(
  campaignId: string,
  fromVersion: number,
  toVersion: number,
  signal?: AbortSignal,
) {
  return apiRequest(
    `/campaigns/${encodeURIComponent(campaignId)}/versions/${fromVersion}/diff/${toVersion}`,
    versionDiff,
    { signal },
  );
}
