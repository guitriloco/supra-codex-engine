#include <gtest/gtest.h>
#include "wraith/modules/modules.h"

using namespace wraith;

TEST(HttpScraperTest, ReturnsStubResponse) {
    TaskConfig config;
    config.id = "scrape-test";
    config.type = "scrape";
    config.target = "https://example.com";

    auto result = modules::http_scrape(config);
    EXPECT_TRUE(result.success);
    EXPECT_FALSE(result.data.empty());
}

TEST(DataEnricherTest, ReturnsStubResponse) {
    TaskConfig config;
    config.id = "enrich-test";
    config.type = "enrich";
    config.payload = "raw data";

    auto result = modules::data_enrich(config);
    EXPECT_TRUE(result.success);
}

TEST(RateLimiterTest, AllowsByDefault) {
    TaskConfig config;
    config.id = "ratelimit-test";
    config.type = "rate_limit";

    auto result = modules::rate_limit_check(config);
    EXPECT_TRUE(result.success);
}